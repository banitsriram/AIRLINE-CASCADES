-- On-time performance per day (on-time = delay_minutes <= 15, the industry-standard threshold).
SELECT
  DATE(sched_departure) AS flight_date,
  COUNT(*) AS total_flights,
  SUM(CASE WHEN delay_minutes <= 15 THEN 1 ELSE 0 END) AS on_time_flights,
  ROUND(100 * SUM(CASE WHEN delay_minutes <= 15 THEN 1 ELSE 0 END) / COUNT(*), 1) AS on_time_pct
FROM flight
WHERE status <> 'CANCELLED'
GROUP BY DATE(sched_departure)
ORDER BY flight_date;
