-- Passengers affected by a cascade rooted at a given flight.
-- Runs for the flight of the first delay notice; set @flight_id to use another.
SET @flight_id = (SELECT flight_id FROM flight_delay ORDER BY delay_id LIMIT 1);

WITH RECURSIVE cascade_tree AS (
  SELECT flight_id FROM flight WHERE flight_id = @flight_id
  UNION ALL
  SELECT f.flight_id FROM flight f
  JOIN cascade_tree ct ON f.parent_flight_id = ct.flight_id
)
SELECT DISTINCT p.passenger_id, p.name, p.email, t.flight_id, t.seat_no, t.class
FROM cascade_tree ct
JOIN ticket t ON t.flight_id = ct.flight_id
JOIN booking b ON b.booking_id = t.booking_id AND b.status = 'CONFIRMED'
JOIN passenger p ON p.passenger_id = b.passenger_id
ORDER BY t.flight_id, p.name;
