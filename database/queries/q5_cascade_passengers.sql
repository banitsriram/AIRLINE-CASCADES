-- Passengers affected by a cascade rooted at a given flight.
-- Example below is for flight_id = 1.
WITH RECURSIVE cascade_tree AS (
  SELECT flight_id FROM flight WHERE flight_id = 1
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
