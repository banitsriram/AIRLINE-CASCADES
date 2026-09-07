DELIMITER $$

-- P0: Simulate a delay on a flight and iteratively propagate it to every downstream
-- flight sharing the same aircraft (multi-hop). Implemented as a stored procedure
-- (not a trigger) -- see the note in 04_triggers.sql for why. Each pass of the WHILE
-- loop extends delay_minutes on any flight whose scheduled departure now falls
-- inside a delayed predecessor's new (delayed) arrival window; the loop stops once a
-- pass changes nothing (ROW_COUNT() = 0). delay_minutes only ever increases, so this
-- always terminates; the iteration cap is a defensive backstop.
CREATE PROCEDURE simulate_delay(IN p_flight_id INT, IN p_minutes INT, IN p_reason_id INT)
BEGIN
  DECLARE v_changed INT DEFAULT 1;
  DECLARE v_guard INT DEFAULT 0;

  INSERT INTO flight_delay (flight_id, reason_id, minutes)
  VALUES (p_flight_id, p_reason_id, p_minutes);

  UPDATE flight
  SET delay_minutes = delay_minutes + p_minutes
  WHERE flight_id = p_flight_id;

  WHILE v_changed > 0 AND v_guard < 50 DO
    UPDATE flight downstream
    JOIN flight origin
      ON downstream.aircraft_id = origin.aircraft_id
     AND downstream.flight_id <> origin.flight_id
     AND downstream.sched_departure > origin.sched_arrival
     AND downstream.sched_departure < DATE_ADD(origin.sched_arrival, INTERVAL origin.delay_minutes MINUTE)
     AND downstream.delay_minutes < TIMESTAMPDIFF(MINUTE, downstream.sched_departure,
           DATE_ADD(origin.sched_arrival, INTERVAL origin.delay_minutes MINUTE))
    SET downstream.parent_flight_id = origin.flight_id,
        downstream.delay_minutes = TIMESTAMPDIFF(MINUTE, downstream.sched_departure,
          DATE_ADD(origin.sched_arrival, INTERVAL origin.delay_minutes MINUTE));

    SET v_changed = ROW_COUNT();
    SET v_guard = v_guard + 1;
  END WHILE;
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

  SET p_pnr = UPPER(SUBSTRING(MD5(RAND()), 1, 6));

  INSERT INTO booking (pnr, passenger_id, status)
  VALUES (p_pnr, p_passenger_id, 'CONFIRMED');
  SET v_booking_id = LAST_INSERT_ID();

  INSERT INTO ticket (booking_id, flight_id, seat_no, fare, class)
  VALUES (v_booking_id, p_flight_id, p_seat_no, p_fare, p_class);

  COMMIT;
END$$

DELIMITER ;
