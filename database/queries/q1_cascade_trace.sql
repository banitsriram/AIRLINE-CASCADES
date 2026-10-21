-- Recursive cascade trace: every flight downstream of a delayed flight, via parent_flight_id.
-- Runs for the flight of the first delay notice; set @flight_id to trace another.
-- The app calls the equivalent stored procedure, analyse_cascade(flight_id).
SET @flight_id = (SELECT flight_id FROM flight_delay ORDER BY delay_id LIMIT 1);

WITH RECURSIVE cascade_tree AS (
  SELECT flight_id, flight_number, parent_flight_id,
         sched_departure, delay_minutes, 0 AS cascade_depth
  FROM flight
  WHERE flight_id = @flight_id
  UNION ALL
  SELECT f.flight_id, f.flight_number, f.parent_flight_id,
         f.sched_departure, f.delay_minutes, ct.cascade_depth + 1
  FROM flight f
  INNER JOIN cascade_tree ct ON f.parent_flight_id = ct.flight_id
)
SELECT * FROM cascade_tree ORDER BY cascade_depth, sched_departure;
