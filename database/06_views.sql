-- Estimated times and operational flags are derived here, never stored, so
-- they can't drift from delay_minutes.

CREATE VIEW v_flight_times AS
SELECT f.flight_id, f.flight_number, f.status, f.delay_minutes, f.parent_flight_id,
       f.aircraft_id, ac.registration, f.gate_id, g.gate_code, f.remarks, f.route_id,
       r.origin_airport_id, r.dest_airport_id, o.iata_code AS origin, d.iata_code AS dest,
       f.sched_departure AS std, f.sched_arrival AS sta,
       DATE_ADD(f.sched_departure, INTERVAL f.delay_minutes MINUTE) AS etd,
       DATE_ADD(f.sched_arrival, INTERVAL f.delay_minutes MINUTE) AS eta,
       f.boarding_start, f.actual_departure, f.actual_arrival,
       -- Any status other than SCHEDULED is shown as-is, so a value added to the
       -- ENUM later (ALTER TABLE) appears without changing this view.
       CASE WHEN f.status <> 'SCHEDULED' THEN f.status
            WHEN f.delay_minutes > 0 THEN 'DELAYED'
            ELSE 'ON TIME' END AS display_status
FROM flight f
JOIN route r ON r.route_id = f.route_id
JOIN airport o ON o.airport_id = r.origin_airport_id
JOIN airport d ON d.airport_id = r.dest_airport_id
JOIN aircraft ac ON ac.aircraft_id = f.aircraft_id
LEFT JOIN gate g ON g.gate_id = f.gate_id;

-- Connecting passengers whose onward flight now leaves too soon after they
-- land (less than the connecting airport's minimum connection time), or whose
-- onward flight was cancelled.
CREATE VIEW v_missed_connections AS
SELECT b.booking_id, b.pnr, p.passenger_id, p.name AS passenger_name,
       f1.flight_id AS in_flight_id, f1.flight_number AS in_flight,
       f2.flight_id AS out_flight_id, f2.flight_number AS out_flight,
       f1.dest AS connect_airport, f1.eta AS in_eta, f2.etd AS out_etd,
       TIMESTAMPDIFF(MINUTE, f1.eta, f2.etd) AS connect_min,
       ap.min_connect_min
FROM booking b
JOIN passenger p ON p.passenger_id = b.passenger_id
JOIN ticket t1 ON t1.booking_id = b.booking_id
JOIN ticket t2 ON t2.booking_id = b.booking_id AND t2.ticket_id <> t1.ticket_id
JOIN v_flight_times f1 ON f1.flight_id = t1.flight_id
JOIN v_flight_times f2 ON f2.flight_id = t2.flight_id
JOIN airport ap ON ap.airport_id = f1.dest_airport_id
WHERE b.status IN ('CONFIRMED', 'CHECKED_IN')
  AND f2.origin_airport_id = f1.dest_airport_id
  AND f2.std > f1.std
  AND f2.std < DATE_ADD(f1.sta, INTERVAL 1 DAY)
  AND (f2.status = 'CANCELLED'
       OR TIMESTAMPDIFF(MINUTE, f1.eta, f2.etd) < ap.min_connect_min);

-- Crew whose flight duty (first ETD to last ETA of the day) exceeds 13 h,
-- the DGCA-style flight duty period limit.
CREATE VIEW v_duty_breaches AS
SELECT ca.crew_id, c.name, c.role, DATE(ft.std) AS duty_date,
       MIN(ft.etd) AS duty_start, MAX(ft.eta) AS duty_end,
       ROUND(TIMESTAMPDIFF(MINUTE, MIN(ft.etd), MAX(ft.eta)) / 60, 2) AS duty_hours,
       COUNT(*) AS legs
FROM crew_assignment ca
JOIN crew c ON c.crew_id = ca.crew_id
JOIN v_flight_times ft ON ft.flight_id = ca.flight_id
WHERE ca.unassigned_at IS NULL AND ft.status <> 'CANCELLED'
GROUP BY ca.crew_id, c.name, c.role, DATE(ft.std)
HAVING duty_hours > 13;

-- Flights now departing or arriving outside an airport's opening hours.
CREATE VIEW v_curfew_risk AS
SELECT ft.flight_id, ft.flight_number, 'DEPARTURE' AS side, ft.origin AS airport,
       ft.etd AS at_time, ap.open_time, ap.close_time
FROM v_flight_times ft
JOIN airport ap ON ap.airport_id = ft.origin_airport_id
WHERE ft.status IN ('SCHEDULED', 'BOARDING')
  AND ap.open_time IS NOT NULL
  AND (TIME(ft.etd) < ap.open_time OR TIME(ft.etd) > ap.close_time)
UNION ALL
SELECT ft.flight_id, ft.flight_number, 'ARRIVAL', ft.dest,
       ft.eta, ap.open_time, ap.close_time
FROM v_flight_times ft
JOIN airport ap ON ap.airport_id = ft.dest_airport_id
WHERE ft.status IN ('SCHEDULED', 'BOARDING', 'DEPARTED')
  AND ap.open_time IS NOT NULL
  AND (TIME(ft.eta) < ap.open_time OR TIME(ft.eta) > ap.close_time);
