-- Recursive CTEs below go up to n=5000 (tickets); default depth limit is 1000.
-- Note: MySQL requires WITH to directly precede the SELECT it feeds, so for
-- INSERT ... SELECT the WITH clause goes AFTER "INSERT INTO t (cols)", not before it.
SET SESSION cte_max_recursion_depth = 10000;

-- ============= AIRCRAFT (15) =============
INSERT INTO aircraft (registration, type_id, base_airport_id, status)
WITH RECURSIVE seq AS (
  SELECT 1 AS n UNION ALL SELECT n + 1 FROM seq WHERE n < 15
)
SELECT CONCAT('VT-AC', LPAD(n, 2, '0')), ((n - 1) % 4) + 1, ((n - 1) % 12) + 1, 'ACTIVE'
FROM seq;

-- ============= ROUTES (~30) =============
-- 4 guaranteed routes for the cascade demo (DEL=1, BOM=2, BLR=3, MAA=4)
INSERT INTO route (origin_airport_id, dest_airport_id, distance_km, std_duration_min) VALUES
(1, 2, 1150, 130),  -- DEL -> BOM
(2, 3, 840, 105),   -- BOM -> BLR
(3, 4, 290, 60),     -- BLR -> MAA
(4, 1, 1760, 150);  -- MAA -> DEL

INSERT IGNORE INTO route (origin_airport_id, dest_airport_id, distance_km, std_duration_min)
WITH RECURSIVE seq AS (
  SELECT 1 AS n UNION ALL SELECT n + 1 FROM seq WHERE n < 12
),
raw_pairs AS (
  SELECT o.n AS o, ((o.n + k.n - 1) % 12) + 1 AS d
  FROM seq o
  CROSS JOIN (SELECT 1 AS n UNION ALL SELECT 2 UNION ALL SELECT 3) k
),
pairs AS (
  SELECT o, d, 300 + ((o * 97 + d * 61) % 1700) AS distance_km
  FROM raw_pairs
  WHERE o <> d
)
SELECT o, d, distance_km, FLOOR(distance_km / 12) + 30
FROM pairs;

-- ============= CREW (60) =============
INSERT INTO crew (name, role, base_airport_id, hire_date)
WITH RECURSIVE seq AS (
  SELECT 1 AS n UNION ALL SELECT n + 1 FROM seq WHERE n < 60
)
SELECT
  CONCAT(
    ELT(((n - 1) % 15) + 1, 'Aarav','Vivaan','Aditya','Vihaan','Arjun','Sai','Reyansh','Krishna','Ishaan','Rohan','Ananya','Diya','Priya','Kavya','Meera'),
    ' ',
    ELT(((n * 7 - 1) % 15) + 1, 'Sharma','Verma','Iyer','Nair','Reddy','Rao','Gupta','Mehta','Joshi','Kulkarni','Menon','Pillai','Chawla','Bhatt','Desai')
  ),
  ELT(((n - 1) % 6) + 1, 'CAPTAIN','FIRST_OFFICER','CABIN_CREW','CABIN_CREW','CABIN_CREW','PURSER'),
  ((n - 1) % 12) + 1,
  DATE_SUB(CURDATE(), INTERVAL (365 * 2 + n * 11) DAY)
FROM seq;

-- ============= CREW CERTIFICATIONS (~90) =============
INSERT INTO crew_certification (crew_id, type_id, certified_date, expiry_date)
WITH RECURSIVE seq AS (
  SELECT 1 AS n UNION ALL SELECT n + 1 FROM seq WHERE n < 60
)
SELECT n, ((n - 1) % 4) + 1,
       DATE_SUB(CURDATE(), INTERVAL (200 + n * 3) DAY),
       DATE_ADD(CURDATE(), INTERVAL (200 + n * 5) DAY)
FROM seq
UNION ALL
SELECT n, (n % 4) + 1,
       DATE_SUB(CURDATE(), INTERVAL (150 + n * 2) DAY),
       DATE_ADD(CURDATE(), INTERVAL (250 + n * 4) DAY)
FROM seq
WHERE n % 2 = 0;

-- ============= FLIGHTS (300) =============
-- 4 guaranteed cascade-demo flights on aircraft_id 1, today
INSERT INTO flight (flight_number, route_id, aircraft_id, sched_departure, sched_arrival, status, delay_minutes) VALUES
('AI-101', 1, 1, TIMESTAMP(CURDATE(), '08:00:00'), DATE_ADD(TIMESTAMP(CURDATE(), '08:00:00'), INTERVAL 130 MINUTE), 'SCHEDULED', 0),
('AI-205', 2, 1, TIMESTAMP(CURDATE(), '11:00:00'), DATE_ADD(TIMESTAMP(CURDATE(), '11:00:00'), INTERVAL 105 MINUTE), 'SCHEDULED', 0),
('AI-318', 3, 1, TIMESTAMP(CURDATE(), '15:00:00'), DATE_ADD(TIMESTAMP(CURDATE(), '15:00:00'), INTERVAL 60 MINUTE), 'SCHEDULED', 0),
('AI-422', 4, 1, TIMESTAMP(CURDATE(), '18:30:00'), DATE_ADD(TIMESTAMP(CURDATE(), '18:30:00'), INTERVAL 150 MINUTE), 'SCHEDULED', 0);

-- 296 generated flights across a 7-day window, aircraft 2-15 only (aircraft 1 reserved for the demo above)
INSERT INTO flight (flight_number, route_id, aircraft_id, sched_departure, sched_arrival,
                     actual_departure, actual_arrival, status, delay_minutes)
WITH RECURSIVE seq AS (
  SELECT 1 AS n UNION ALL SELECT n + 1 FROM seq WHERE n < 296
),
gen AS (
  SELECT
    n,
    ((n - 1) % 14) + 2 AS aircraft_id,
    ((n - 1) % 7) AS day_offset,
    6 + ((n * 37) % 14) AS dep_hour,
    (n * 13) % 60 AS dep_minute,
    CASE
      WHEN n % 30 = 0 THEN 'CANCELLED'
      WHEN n % 17 = 0 THEN 'ARRIVED'
      WHEN n % 11 = 0 THEN 'BOARDING'
      ELSE 'SCHEDULED'
    END AS status,
    CASE WHEN n % 9 = 0 THEN 5 + (n % 40) ELSE 0 END AS delay_minutes
  FROM seq
),
routes_numbered AS (
  SELECT route_id, std_duration_min,
         ROW_NUMBER() OVER (ORDER BY route_id) AS rn,
         COUNT(*) OVER () AS total
  FROM route
)
SELECT
  CONCAT('AI-', LPAD(500 + gen.n, 3, '0')),
  rn2.route_id,
  gen.aircraft_id,
  TIMESTAMP(DATE_ADD(CURDATE(), INTERVAL gen.day_offset DAY), MAKETIME(gen.dep_hour, gen.dep_minute, 0)),
  DATE_ADD(TIMESTAMP(DATE_ADD(CURDATE(), INTERVAL gen.day_offset DAY), MAKETIME(gen.dep_hour, gen.dep_minute, 0)), INTERVAL rn2.std_duration_min MINUTE),
  CASE WHEN gen.status = 'ARRIVED'
       THEN DATE_ADD(TIMESTAMP(DATE_ADD(CURDATE(), INTERVAL gen.day_offset DAY), MAKETIME(gen.dep_hour, gen.dep_minute, 0)), INTERVAL gen.delay_minutes MINUTE)
       ELSE NULL END,
  CASE WHEN gen.status = 'ARRIVED'
       THEN DATE_ADD(DATE_ADD(TIMESTAMP(DATE_ADD(CURDATE(), INTERVAL gen.day_offset DAY), MAKETIME(gen.dep_hour, gen.dep_minute, 0)), INTERVAL rn2.std_duration_min MINUTE), INTERVAL gen.delay_minutes MINUTE)
       ELSE NULL END,
  gen.status,
  gen.delay_minutes
FROM gen
JOIN routes_numbered rn2 ON rn2.rn = ((gen.n - 1) % rn2.total) + 1;

-- ============= PASSENGERS (500) =============
INSERT INTO passenger (name, passport_no, email, phone, date_of_birth)
WITH RECURSIVE seq AS (
  SELECT 1 AS n UNION ALL SELECT n + 1 FROM seq WHERE n < 500
)
SELECT
  CONCAT(
    ELT(((n - 1) % 15) + 1, 'Aarav','Vivaan','Aditya','Vihaan','Arjun','Sai','Reyansh','Krishna','Ishaan','Rohan','Ananya','Diya','Priya','Kavya','Meera'),
    ' ',
    ELT(((n * 7 - 1) % 15) + 1, 'Sharma','Verma','Iyer','Nair','Reddy','Rao','Gupta','Mehta','Joshi','Kulkarni','Menon','Pillai','Chawla','Bhatt','Desai')
  ),
  CONCAT('P', LPAD(n, 8, '0')),
  CONCAT('passenger', n, '@example.com'),
  CONCAT('98', LPAD(10000000 + n, 8, '0')),
  DATE_SUB(CURDATE(), INTERVAL (365 * 18 + ((n * 137) % (365 * 57))) DAY)
FROM seq;

-- ============= BOOKINGS + TICKETS (~5000) =============
INSERT INTO booking (pnr, passenger_id, booking_date, status)
WITH RECURSIVE seq AS (
  SELECT 1 AS n UNION ALL SELECT n + 1 FROM seq WHERE n < 5000
),
tgen AS (
  SELECT
    n,
    CONCAT('PN', LPAD(UPPER(CONV(n, 10, 36)), 4, '0')) AS pnr,
    ((n - 1) % 500) + 1 AS passenger_id,
    CASE WHEN n % 47 = 0 THEN 'CANCELLED'
         WHEN n % 31 = 0 THEN 'CHECKED_IN'
         ELSE 'CONFIRMED' END AS b_status
  FROM seq
)
SELECT pnr, passenger_id, DATE_SUB(CURDATE(), INTERVAL (n % 60) DAY), b_status
FROM tgen;

INSERT INTO ticket (booking_id, flight_id, seat_no, fare, class)
WITH RECURSIVE seq AS (
  SELECT 1 AS n UNION ALL SELECT n + 1 FROM seq WHERE n < 5000
),
tgen AS (
  SELECT
    n,
    CONCAT('PN', LPAD(UPPER(CONV(n, 10, 36)), 4, '0')) AS pnr,
    ((n - 1) % 300) + 1 AS flight_id,
    FLOOR((n - 1) / 300) + 1 AS seat_seq
  FROM seq
),
seatgen AS (
  SELECT
    n, pnr, flight_id,
    CEIL(seat_seq / 6) AS seat_row,
    ELT(((seat_seq - 1) % 6) + 1, 'A','B','C','D','E','F') AS seat_letter
  FROM tgen
)
SELECT
  b.booking_id,
  s.flight_id,
  CONCAT(s.seat_row, s.seat_letter),
  CASE
    WHEN s.seat_row = 1 THEN 15000 + (s.n % 5000)
    WHEN s.seat_row = 2 THEN 9000 + (s.n % 3000)
    ELSE 4000 + (s.n % 2000)
  END,
  CASE
    WHEN s.seat_row = 1 THEN 'BUSINESS'
    WHEN s.seat_row = 2 THEN 'PREMIUM'
    ELSE 'ECONOMY'
  END
FROM seatgen s
JOIN booking b ON b.pnr = s.pnr;

-- ============= CREW ASSIGNMENTS (300 flights x 4 crew) =============
INSERT INTO crew_assignment (flight_id, crew_id, role)
WITH RECURSIVE seq AS (
  SELECT 1 AS n UNION ALL SELECT n + 1 FROM seq WHERE n < 300
),
slots AS (
  SELECT 0 AS slot, 'CAPTAIN' AS role UNION ALL
  SELECT 1, 'FIRST_OFFICER' UNION ALL
  SELECT 2, 'CABIN_CREW' UNION ALL
  SELECT 3, 'CABIN_CREW'
)
SELECT seq.n, ((seq.n - 1 + slots.slot * 15) % 60) + 1, slots.role
FROM seq
CROSS JOIN slots;

-- ============= FLIGHT DELAYS (20 pre-existing, for report data) =============
INSERT INTO flight_delay (flight_id, reason_id, minutes, recorded_at, resolved_at)
WITH RECURSIVE seq AS (
  SELECT 1 AS n UNION ALL SELECT n + 1 FROM seq WHERE n < 20
)
SELECT
  ((n * 13) % 300) + 1,
  ((n - 1) % 8) + 1,
  10 + (n * 7) % 90,
  DATE_SUB(NOW(), INTERVAL (n * 3) DAY),
  CASE WHEN n % 3 = 0 THEN DATE_SUB(NOW(), INTERVAL (n * 3 - 1) DAY) ELSE NULL END
FROM seq;

-- ============= MAINTENANCE LOGS (1 per aircraft) =============
INSERT INTO maintenance_log (aircraft_id, maint_start, maint_end, type)
WITH RECURSIVE seq AS (
  SELECT 1 AS n UNION ALL SELECT n + 1 FROM seq WHERE n < 15
)
SELECT
  n,
  DATE_SUB(NOW(), INTERVAL (n * 20 + 5) DAY),
  DATE_SUB(NOW(), INTERVAL (n * 20) DAY),
  ELT(((n - 1) % 7) + 1, 'SCHEDULED','UNSCHEDULED','A_CHECK','B_CHECK','C_CHECK','D_CHECK','LINE_MAINTENANCE')
FROM seq;
