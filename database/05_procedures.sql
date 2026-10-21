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

-- P4: Move the operation forward to p_now. Flights whose boarding time, ETD or
-- ETA has passed become BOARDING, DEPARTED or ARRIVED, with actual times taken
-- from the estimates. Arrivals fire trg_update_duty, so crew duty hours build up
-- as the clock runs. Notices on flights that have left are closed, and bookings
-- whose every leg has landed are completed. Never moves anything backwards.
CREATE PROCEDURE advance_clock(IN p_now DATETIME)
BEGIN
  DECLARE v_boarding INT DEFAULT 0;
  DECLARE v_departed INT DEFAULT 0;
  DECLARE v_arrived INT DEFAULT 0;
  DECLARE v_resolved INT DEFAULT 0;
  DECLARE v_completed INT DEFAULT 0;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  START TRANSACTION;

  UPDATE flight
  SET status = 'DEPARTED',
      actual_departure = DATE_ADD(sched_departure, INTERVAL delay_minutes MINUTE)
  WHERE status IN ('SCHEDULED', 'BOARDING')
    AND DATE_ADD(sched_departure, INTERVAL delay_minutes MINUTE) <= p_now;
  SET v_departed = ROW_COUNT();

  UPDATE flight
  SET status = 'ARRIVED',
      actual_arrival = DATE_ADD(sched_arrival, INTERVAL delay_minutes MINUTE)
  WHERE status = 'DEPARTED'
    AND DATE_ADD(sched_arrival, INTERVAL delay_minutes MINUTE) <= p_now;
  SET v_arrived = ROW_COUNT();

  UPDATE flight
  SET status = 'BOARDING'
  WHERE status = 'SCHEDULED'
    AND DATE_ADD(COALESCE(boarding_start, DATE_SUB(sched_departure, INTERVAL 45 MINUTE)),
                 INTERVAL delay_minutes MINUTE) <= p_now;
  SET v_boarding = ROW_COUNT();

  UPDATE flight_delay fd
  JOIN flight f ON f.flight_id = fd.flight_id
  SET fd.resolved_at = CURRENT_TIMESTAMP
  WHERE fd.resolved_at IS NULL AND f.status IN ('DEPARTED', 'ARRIVED', 'DIVERTED');
  SET v_resolved = ROW_COUNT();

  UPDATE booking b
  SET b.status = 'COMPLETED'
  WHERE b.status IN ('CONFIRMED', 'CHECKED_IN')
    AND EXISTS (SELECT 1 FROM ticket t WHERE t.booking_id = b.booking_id)
    AND NOT EXISTS (SELECT 1 FROM ticket t JOIN flight f ON f.flight_id = t.flight_id
                    WHERE t.booking_id = b.booking_id AND f.status <> 'ARRIVED');
  SET v_completed = ROW_COUNT();

  COMMIT;
  SELECT v_boarding AS boarding, v_departed AS departed, v_arrived AS arrived,
         v_resolved AS notices_closed, v_completed AS bookings_completed;
END$$

-- P5: Rebook one ticket onto the earliest later flight on the same route that
-- the passenger can still make and that has a free seat. For a connecting
-- journey "can still make" means departing at least the airport's minimum
-- connection time after the inbound leg's current ETA; otherwise it means
-- departing no earlier than the original flight. The seat is the lowest free
-- one in the ticket's own cabin band where possible. The move is logged to
-- rebooking.
CREATE PROCEDURE rebook_ticket(
  IN p_ticket_id INT,
  IN p_reason VARCHAR(20),
  OUT p_new_flight_id INT
)
BEGIN
  DECLARE v_booking_id INT;
  DECLARE v_old_flight INT;
  DECLARE v_old_seat VARCHAR(4);
  DECLARE v_class VARCHAR(10);
  DECLARE v_route INT;
  DECLARE v_origin INT;
  DECLARE v_old_etd DATETIME;
  DECLARE v_in_eta DATETIME;
  DECLARE v_mct INT;
  DECLARE v_earliest DATETIME;
  DECLARE v_capacity INT;
  DECLARE v_seat VARCHAR(4);
  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  START TRANSACTION;

  SELECT t.booking_id, t.flight_id, t.seat_no, t.class, ft.route_id, ft.origin_airport_id, ft.etd
  INTO v_booking_id, v_old_flight, v_old_seat, v_class, v_route, v_origin, v_old_etd
  FROM ticket t JOIN v_flight_times ft ON ft.flight_id = t.flight_id
  WHERE t.ticket_id = p_ticket_id
  FOR UPDATE;
  IF v_booking_id IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Ticket not found';
  END IF;

  -- Inbound leg of the same booking that lands at this flight's origin
  SELECT MAX(fi.eta) INTO v_in_eta
  FROM ticket ti JOIN v_flight_times fi ON fi.flight_id = ti.flight_id
  WHERE ti.booking_id = v_booking_id AND ti.ticket_id <> p_ticket_id
    AND fi.dest_airport_id = v_origin AND fi.eta <= DATE_ADD(v_old_etd, INTERVAL 1 DAY)
    AND fi.std < v_old_etd;
  SELECT min_connect_min INTO v_mct FROM airport WHERE airport_id = v_origin;
  SET v_earliest = IF(v_in_eta IS NULL, v_old_etd, DATE_ADD(v_in_eta, INTERVAL v_mct MINUTE));

  SELECT ft.flight_id, at.seat_capacity INTO p_new_flight_id, v_capacity
  FROM v_flight_times ft
  JOIN aircraft ac ON ac.aircraft_id = ft.aircraft_id
  JOIN aircraft_type at ON at.type_id = ac.type_id
  WHERE ft.route_id = v_route
    AND ft.flight_id <> v_old_flight
    AND ft.status = 'SCHEDULED'
    AND ft.etd >= v_earliest
    AND (SELECT COUNT(*) FROM ticket t2 JOIN booking b2 ON b2.booking_id = t2.booking_id
         WHERE t2.flight_id = ft.flight_id AND b2.status <> 'CANCELLED') < at.seat_capacity
  ORDER BY ft.etd, ft.flight_id
  LIMIT 1;
  IF p_new_flight_id IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'No later flight on this route in the schedule has a free seat';
  END IF;

  -- Lock the new flight so two rebookings can't pick the same seat
  SELECT flight_id INTO p_new_flight_id FROM flight WHERE flight_id = p_new_flight_id FOR UPDATE;

  -- Seats are numbered 1A..nF, six abreast: rows 1 business, 2 premium, 3+ economy
  SET v_seat = (
    WITH RECURSIVE seat AS (
      SELECT 1 AS n UNION ALL SELECT n + 1 FROM seat WHERE n < v_capacity
    )
    SELECT CONCAT(CEIL(n / 6), ELT(((n - 1) % 6) + 1, 'A','B','C','D','E','F'))
    FROM seat
    WHERE CONCAT(CEIL(n / 6), ELT(((n - 1) % 6) + 1, 'A','B','C','D','E','F')) NOT IN
          (SELECT seat_no FROM ticket WHERE flight_id = p_new_flight_id)
    ORDER BY CASE v_class
               WHEN 'FIRST'    THEN n > 6
               WHEN 'BUSINESS' THEN n > 6
               WHEN 'PREMIUM'  THEN NOT (n BETWEEN 7 AND 12)
               ELSE n <= 12 END,
             n
    LIMIT 1);
  IF v_seat IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'No free seat on the replacement flight';
  END IF;

  UPDATE ticket
  SET flight_id = p_new_flight_id, seat_no = v_seat, checked_in_at = NULL, boarded_at = NULL
  WHERE ticket_id = p_ticket_id;

  INSERT INTO rebooking (ticket_id, old_flight_id, new_flight_id, old_seat_no, new_seat_no, reason)
  VALUES (p_ticket_id, v_old_flight, p_new_flight_id, v_old_seat, v_seat, p_reason);

  COMMIT;
END$$

DELIMITER ;
