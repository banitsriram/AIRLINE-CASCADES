DELIMITER $$

-- The four cascade rules, evaluated against current ETD/ETA. Fills
-- cascade_candidate with the delay each rule requires of every not-yet-departed
-- flight (<= current delay means the rule is satisfied). Called once per pass by
-- simulate_delay(); tests call it directly to check the schedule is consistent.
CREATE PROCEDURE compute_cascade_candidates()
BEGIN
  DELETE FROM cascade_candidate;

  -- AIRCRAFT: previous leg of the same aircraft (by schedule)
  INSERT INTO cascade_candidate (flight_id, cause_flight_id, link, required_delay)
  SELECT b.flight_id, a.flight_id, 'AIRCRAFT',
         TIMESTAMPDIFF(MINUTE, b.std, DATE_ADD(a.eta, INTERVAL ap.min_turnaround_min MINUTE))
  FROM (SELECT flight_id, std, status, origin_airport_id,
               LAG(flight_id) OVER (PARTITION BY aircraft_id ORDER BY std, flight_id) AS prev_id
        FROM v_flight_times WHERE status <> 'CANCELLED') b
  JOIN v_flight_times a ON a.flight_id = b.prev_id
  JOIN airport ap ON ap.airport_id = b.origin_airport_id
  WHERE b.status IN ('SCHEDULED', 'BOARDING');

  -- CREW: each active crew member's previous flight (by schedule)
  INSERT INTO cascade_candidate (flight_id, cause_flight_id, link, required_delay)
  SELECT b.flight_id, a.flight_id, 'CREW',
         TIMESTAMPDIFF(MINUTE, b.std, DATE_ADD(a.eta, INTERVAL 45 MINUTE))
  FROM (SELECT ft.flight_id, ft.std, ft.status,
               LAG(ft.flight_id) OVER (PARTITION BY ca.crew_id ORDER BY ft.std, ft.flight_id) AS prev_id
        FROM crew_assignment ca
        JOIN v_flight_times ft ON ft.flight_id = ca.flight_id
        WHERE ca.unassigned_at IS NULL AND ft.status <> 'CANCELLED') b
  JOIN v_flight_times a ON a.flight_id = b.prev_id
  WHERE b.status IN ('SCHEDULED', 'BOARDING');

  -- GATE: previous departure from the same gate (by schedule)
  INSERT INTO cascade_candidate (flight_id, cause_flight_id, link, required_delay)
  SELECT b.flight_id, a.flight_id, 'GATE',
         TIMESTAMPDIFF(MINUTE, b.boarding_sched, DATE_ADD(a.etd, INTERVAL 10 MINUTE))
  FROM (SELECT flight_id, status,
               COALESCE(boarding_start, DATE_SUB(std, INTERVAL 45 MINUTE)) AS boarding_sched,
               LAG(flight_id) OVER (PARTITION BY gate_id ORDER BY std, flight_id) AS prev_id
        FROM v_flight_times WHERE gate_id IS NOT NULL AND status <> 'CANCELLED') b
  JOIN v_flight_times a ON a.flight_id = b.prev_id
  WHERE b.status IN ('SCHEDULED', 'BOARDING');

  -- SLOT: departures per airport per clock hour of ETD; undelayed flights keep
  -- their slots, delayed ones beyond the limit move to the start of the next hour
  INSERT INTO cascade_candidate (flight_id, cause_flight_id, link, required_delay)
  SELECT x.flight_id, NULL, 'SLOT',
         TIMESTAMPDIFF(MINUTE, x.std, DATE_ADD(x.hour_start, INTERVAL 1 HOUR))
  FROM (SELECT ft.flight_id, ft.std, ft.status, ap.runway_slots_per_hour AS cap,
               TIMESTAMP(DATE(ft.etd), MAKETIME(HOUR(ft.etd), 0, 0)) AS hour_start,
               ROW_NUMBER() OVER (PARTITION BY ft.origin_airport_id, DATE(ft.etd), HOUR(ft.etd)
                                  ORDER BY ft.delay_minutes > 0, ft.etd, ft.flight_id) AS slot_rank
        FROM v_flight_times ft
        JOIN airport ap ON ap.airport_id = ft.origin_airport_id
        WHERE ft.status <> 'CANCELLED') x
  WHERE x.slot_rank > x.cap AND x.status IN ('SCHEDULED', 'BOARDING');
END$$

-- P0: File a delay notice on a flight and cascade it across the whole operation.
-- Implemented as a stored procedure (not a trigger) -- see the note in
-- 04_triggers.sql for why.
--
-- After applying the notice to the flight itself, each pass of the WHILE loop
-- asks four rules what delay every not-yet-departed flight now *requires*:
--   AIRCRAFT  next leg of the same aircraft can't leave before it lands + turnaround
--   CREW      a crew member's next flight can't leave before their previous one
--             lands + 45 min crew connection
--   GATE      the next flight at a gate can't start boarding until the previous
--             one has pushed back + 10 min
--   SLOT      an airport can't exceed runway_slots_per_hour departures in a clock
--             hour; delayed flights beyond the limit move to the next hour
-- The biggest requirement per flight wins, is logged to delay_impact, and raises
-- delay_minutes. The loop stops when a pass changes nothing. delay_minutes only
-- ever increases, so it terminates; the 50-pass cap is a backstop.
--
-- Estimated times are never stored: ETD/ETA = scheduled + delay_minutes (see
-- v_flight_times in 06_views.sql).
CREATE PROCEDURE simulate_delay(
  IN p_flight_id INT,
  IN p_minutes INT,
  IN p_code_id INT,
  IN p_sub_reason VARCHAR(200),
  IN p_phase VARCHAR(20),
  IN p_ops_status VARCHAR(10),
  IN p_new_gate_id INT,
  IN p_new_boarding DATETIME,
  IN p_pax_deboarded BOOLEAN,
  IN p_swap_aircraft_id INT,
  IN p_announcement VARCHAR(500),
  IN p_meal_voucher BOOLEAN,
  IN p_compensation BOOLEAN,
  IN p_rebooking BOOLEAN,
  IN p_reported_by VARCHAR(80),
  IN p_remarks VARCHAR(500),
  OUT p_delay_id INT
)
BEGIN
  DECLARE v_changed INT DEFAULT 1;
  DECLARE v_pass INT DEFAULT 0;
  DECLARE v_status VARCHAR(10);
  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  START TRANSACTION;

  SELECT status INTO v_status FROM flight WHERE flight_id = p_flight_id FOR UPDATE;
  IF v_status IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Flight not found';
  END IF;
  IF v_status IN ('ARRIVED', 'CANCELLED', 'DIVERTED') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Cannot delay a flight that has arrived, diverted or been cancelled';
  END IF;

  INSERT INTO flight_delay (
    flight_id, code_id, minutes, sub_reason, phase, ops_status,
    new_gate_id, new_boarding_time, pax_deboarded, swap_aircraft_id,
    announcement, meal_voucher, compensation_eligible, rebooking_offered,
    reported_by, remarks)
  SELECT p_flight_id, dc.code_id, p_minutes, p_sub_reason, p_phase, p_ops_status,
         p_new_gate_id, p_new_boarding, p_pax_deboarded, p_swap_aircraft_id,
         p_announcement, p_meal_voucher, p_compensation, p_rebooking,
         p_reported_by, p_remarks
  FROM delay_code dc WHERE dc.code_id = p_code_id;
  IF ROW_COUNT() = 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Unknown delay code';
  END IF;
  SET p_delay_id = LAST_INSERT_ID();

  UPDATE flight
  SET delay_minutes = delay_minutes + p_minutes,
      gate_id = COALESCE(p_new_gate_id, gate_id),
      aircraft_id = COALESCE(p_swap_aircraft_id, aircraft_id),
      status = IF(p_ops_status = 'CANCELLED', 'CANCELLED', status)
  WHERE flight_id = p_flight_id;

  -- A cancelled flight doesn't push anything downstream.
  IF p_ops_status = 'CANCELLED' THEN
    SET v_changed = 0;
  END IF;

  WHILE v_changed > 0 AND v_pass < 50 DO
    SET v_pass = v_pass + 1;
    CALL compute_cascade_candidates();

    -- Winning (largest) requirement per flight, where it exceeds the current delay
    INSERT INTO delay_impact (delay_id, flight_id, cause_flight_id, link, minutes_added, old_etd, new_etd, pass_no)
    SELECT p_delay_id, w.flight_id, w.cause_flight_id, w.link,
           w.required_delay - f.delay_minutes,
           DATE_ADD(f.sched_departure, INTERVAL f.delay_minutes MINUTE),
           DATE_ADD(f.sched_departure, INTERVAL w.required_delay MINUTE),
           v_pass
    FROM (SELECT c.*, ROW_NUMBER() OVER (PARTITION BY c.flight_id ORDER BY c.required_delay DESC, c.link) AS rn
          FROM cascade_candidate c) w
    JOIN flight f ON f.flight_id = w.flight_id
    WHERE w.rn = 1 AND w.required_delay > f.delay_minutes;

    UPDATE flight f
    JOIN delay_impact di ON di.flight_id = f.flight_id AND di.delay_id = p_delay_id AND di.pass_no = v_pass
    SET f.delay_minutes = f.delay_minutes + di.minutes_added,
        f.parent_flight_id = COALESCE(di.cause_flight_id, f.parent_flight_id);

    SET v_changed = ROW_COUNT();
  END WHILE;

  DELETE FROM cascade_candidate;
  COMMIT;
END$$

-- Undo every filed delay so the demo can be run again. Gate changes and
-- aircraft swaps made by notices are not reverted (the originals aren't kept);
-- re-run scripts/setup_db.sh for a full reset.
CREATE PROCEDURE reset_all_delays()
BEGIN
  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;
  START TRANSACTION;
  DELETE FROM flight_delay;  -- delay_impact rows go with it (ON DELETE CASCADE)
  UPDATE flight
  SET delay_minutes = 0,
      parent_flight_id = NULL,
      status = IF(status = 'CANCELLED', 'SCHEDULED', status)
  WHERE delay_minutes <> 0 OR parent_flight_id IS NOT NULL OR status = 'CANCELLED';
  COMMIT;
END$$

-- P1: Recursive cascade trace using CTE (MySQL 8.0+)
CREATE PROCEDURE analyse_cascade(IN p_flight_id INT)
BEGIN
  WITH RECURSIVE cascade_tree AS (
    SELECT flight_id, flight_number, parent_flight_id,
           sched_departure, delay_minutes, 0 AS cascade_depth
    FROM flight
    WHERE flight_id = p_flight_id
    UNION ALL
    SELECT f.flight_id, f.flight_number, f.parent_flight_id,
           f.sched_departure, f.delay_minutes, ct.cascade_depth + 1
    FROM flight f
    INNER JOIN cascade_tree ct ON f.parent_flight_id = ct.flight_id
  )
  SELECT * FROM cascade_tree ORDER BY cascade_depth, sched_departure;
END$$

-- P2: Find eligible replacement crew for a given flight
CREATE PROCEDURE find_replacement_crew(IN p_flight_id INT)
BEGIN
  DECLARE v_type_id INT;
  DECLARE v_origin_id INT;
  DECLARE v_sched_dep DATETIME;
  DECLARE v_sched_arr DATETIME;

  SELECT a.type_id, r.origin_airport_id, f.sched_departure, f.sched_arrival
  INTO v_type_id, v_origin_id, v_sched_dep, v_sched_arr
  FROM flight f
  JOIN aircraft a ON a.aircraft_id = f.aircraft_id
  JOIN route r ON r.route_id = f.route_id
  WHERE f.flight_id = p_flight_id;

  SELECT c.crew_id, c.name, c.role
  FROM crew c
  JOIN crew_certification cc ON cc.crew_id = c.crew_id
  WHERE cc.type_id = v_type_id
    AND cc.expiry_date > CURDATE()
    AND c.base_airport_id = v_origin_id
    AND c.terminated_at IS NULL
    AND NOT EXISTS (
      SELECT 1 FROM crew_assignment ca
      JOIN flight f2 ON f2.flight_id = ca.flight_id
      WHERE ca.crew_id = c.crew_id
        AND ca.unassigned_at IS NULL
        AND f2.sched_departure < v_sched_arr
        AND f2.sched_arrival > v_sched_dep
    )
    AND COALESCE(
      (SELECT hours_on_duty FROM duty_log
       WHERE crew_id = c.crew_id AND duty_date = DATE(v_sched_dep)),
      0
    ) < 8;
END$$

-- P3: Transactional ticket booking
CREATE PROCEDURE book_ticket(
  IN p_passenger_id INT,
  IN p_flight_id INT,
  IN p_seat_no VARCHAR(4),
  IN p_class VARCHAR(10),
  IN p_fare DECIMAL(10,2),
  OUT p_pnr CHAR(6)
)
BEGIN
  DECLARE v_booking_id INT;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  START TRANSACTION;

  -- MD5()/SHA1() are unavailable on MySQL builds linked against an OpenSSL 3.x
  -- "default" provider with the legacy provider disabled (common on Homebrew
  -- installs) -- calling either raises "FUNCTION db.MD5 does not exist" even
  -- though the function exists on a standard build. UUID() has no such
  -- dependency and is equally suitable for generating a random PNR. See
  -- DEVIATIONS.md.
  SET p_pnr = UPPER(SUBSTRING(REPLACE(UUID(), '-', ''), 1, 6));

  INSERT INTO booking (pnr, passenger_id, status)
  VALUES (p_pnr, p_passenger_id, 'CONFIRMED');
  SET v_booking_id = LAST_INSERT_ID();

  INSERT INTO ticket (booking_id, flight_id, seat_no, fare, class)
  VALUES (v_booking_id, p_flight_id, p_seat_no, p_fare, p_class);

  COMMIT;
END$$

DELIMITER ;
