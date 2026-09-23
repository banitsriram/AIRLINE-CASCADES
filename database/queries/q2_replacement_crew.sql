-- Eligible replacement crew for a flight: certified on the aircraft type, based at the
-- origin airport, not already assigned to an overlapping flight, and under the duty-hour limit.
-- Example below is for flight_id = 1; the app calls the equivalent stored procedure find_replacement_crew(:flight_id).
SELECT c.crew_id, c.name, c.role
FROM crew c
JOIN crew_certification cc ON cc.crew_id = c.crew_id
JOIN flight f ON f.flight_id = 1
JOIN aircraft a ON a.aircraft_id = f.aircraft_id
JOIN route r ON r.route_id = f.route_id
WHERE cc.type_id = a.type_id
  AND cc.expiry_date > CURDATE()
  AND c.base_airport_id = r.origin_airport_id
  AND c.terminated_at IS NULL
  AND NOT EXISTS (
    SELECT 1 FROM crew_assignment ca
    JOIN flight f2 ON f2.flight_id = ca.flight_id
    WHERE ca.crew_id = c.crew_id
      AND ca.unassigned_at IS NULL
      AND f2.sched_departure < f.sched_arrival
      AND f2.sched_arrival > f.sched_departure
  )
  AND COALESCE(
    (SELECT hours_on_duty FROM duty_log
     WHERE crew_id = c.crew_id AND duty_date = DATE(f.sched_departure)),
    0
  ) < 8;
