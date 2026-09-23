-- NOTE: the spec originally called for a trg_cascade_delay AFTER UPDATE trigger on
-- flight that itself UPDATEs flight. MySQL rejects this at runtime with error 1442
-- ("Can't update table 'flight' in stored function/trigger because it is already
-- used by statement which invoked this stored function/trigger") -- this is a real
-- MySQL restriction, and the spec's claim that MySQL has no mutating-table problem
-- does not hold for a trigger self-modifying its own table. Worse, the original
-- design also depended on the trigger recursively re-firing itself as it updated
-- each downstream flight, to walk multi-hop chains -- MySQL does not support that
-- kind of trigger self-recursion either. The cascade is instead implemented as an
-- iterative stored procedure, simulate_delay() in 05_procedures.sql, called
-- explicitly by the "Simulate Delay" action instead of firing automatically on
-- UPDATE. See DEVIATIONS.md.

DELIMITER $$

CREATE TRIGGER trg_update_duty
AFTER UPDATE ON flight
FOR EACH ROW
BEGIN
  DECLARE v_flown DECIMAL(5,2);
  IF NEW.actual_arrival IS NOT NULL AND OLD.actual_arrival IS NULL THEN
    SET v_flown = TIMESTAMPDIFF(MINUTE, NEW.actual_departure, NEW.actual_arrival) / 60;
    INSERT INTO duty_log (crew_id, duty_date, hours_flown, hours_on_duty)
      SELECT ca.crew_id, DATE(NEW.actual_departure), v_flown, v_flown + 1
      FROM crew_assignment ca
      WHERE ca.flight_id = NEW.flight_id
        AND ca.unassigned_at IS NULL
    ON DUPLICATE KEY UPDATE
      hours_flown = hours_flown + v_flown,
      hours_on_duty = hours_on_duty + v_flown + 1;
  END IF;
END$$

CREATE TRIGGER trg_check_duty_limit
BEFORE INSERT ON crew_assignment
FOR EACH ROW
BEGIN
  DECLARE v_current_hours DECIMAL(5,2) DEFAULT 0;
  DECLARE v_flight_hours DECIMAL(5,2);
  DECLARE v_dep_date DATE;

  SELECT DATE(sched_departure),
         TIMESTAMPDIFF(MINUTE, sched_departure, sched_arrival) / 60
  INTO v_dep_date, v_flight_hours
  FROM flight WHERE flight_id = NEW.flight_id;

  SELECT COALESCE(hours_on_duty, 0) INTO v_current_hours
  FROM duty_log
  WHERE crew_id = NEW.crew_id AND duty_date = v_dep_date;

  IF v_current_hours + v_flight_hours > 11 THEN
    SIGNAL SQLSTATE '45000'
    SET MESSAGE_TEXT = 'Assignment would exceed 11-hour daily duty limit for crew member';
  END IF;
END$$

CREATE TRIGGER trg_no_double_seat
BEFORE INSERT ON ticket
FOR EACH ROW
BEGIN
  DECLARE v_count INT;
  SELECT COUNT(*) INTO v_count
  FROM ticket t
  JOIN booking b ON b.booking_id = t.booking_id
  WHERE t.flight_id = NEW.flight_id
    AND t.seat_no = NEW.seat_no
    AND b.status = 'CONFIRMED';
  IF v_count > 0 THEN
    SIGNAL SQLSTATE '45000'
    SET MESSAGE_TEXT = 'Seat already booked on this flight';
  END IF;
END$$

DELIMITER ;
