-- Crew nearing the 11-hour daily duty limit today.
SELECT
  c.crew_id, c.name, c.role,
  dl.duty_date, dl.hours_on_duty, dl.hours_flown,
  ROUND(11 - dl.hours_on_duty, 2) AS hours_remaining
FROM crew c
JOIN duty_log dl ON dl.crew_id = c.crew_id
WHERE dl.duty_date = CURDATE()
  AND dl.hours_on_duty >= 8
ORDER BY dl.hours_on_duty DESC;
