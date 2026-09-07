-- Load factor (tickets sold / seat capacity) per flight, excluding cancelled bookings.
SELECT
  f.flight_id, f.flight_number, f.sched_departure,
  at.seat_capacity,
  COUNT(t.ticket_id) AS tickets_sold,
  ROUND(100 * COUNT(t.ticket_id) / at.seat_capacity, 1) AS load_factor_pct
FROM flight f
JOIN aircraft a ON a.aircraft_id = f.aircraft_id
JOIN aircraft_type at ON at.type_id = a.type_id
LEFT JOIN (
  SELECT t.ticket_id, t.flight_id
  FROM ticket t
  JOIN booking b ON b.booking_id = t.booking_id
  WHERE b.status <> 'CANCELLED'
) t ON t.flight_id = f.flight_id
GROUP BY f.flight_id, f.flight_number, f.sched_departure, at.seat_capacity
ORDER BY f.sched_departure;
