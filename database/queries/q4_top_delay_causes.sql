-- Aggregate delay minutes by cause category.
SELECT
  dr.category,
  COUNT(*) AS delay_count,
  SUM(fd.minutes) AS total_minutes,
  ROUND(AVG(fd.minutes), 1) AS avg_minutes
FROM flight_delay fd
JOIN delay_code dc ON dc.code_id = fd.code_id
JOIN delay_reason dr ON dr.reason_id = dc.reason_id
GROUP BY dr.category
ORDER BY delay_count DESC;
