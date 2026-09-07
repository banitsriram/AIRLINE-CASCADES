-- Flights operated and scheduled/delay hours per aircraft.
SELECT
  a.aircraft_id, a.registration, at.model,
  COUNT(f.flight_id) AS flights_operated,
  ROUND(SUM(TIMESTAMPDIFF(MINUTE, f.sched_departure, f.sched_arrival)) / 60, 1) AS scheduled_flight_hours,
  ROUND(SUM(f.delay_minutes) / 60, 1) AS total_delay_hours
FROM aircraft a
JOIN aircraft_type at ON at.type_id = a.type_id
LEFT JOIN flight f ON f.aircraft_id = a.aircraft_id AND f.status <> 'CANCELLED'
GROUP BY a.aircraft_id, a.registration, at.model
ORDER BY flights_operated DESC;
