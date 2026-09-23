-- Operational seed: a 7-day hub-and-spoke schedule that satisfies every cascade
-- rule in simulate_delay() with all delays at zero (tests/test_cascade.py checks
-- this), so flights only ever move because of a delay somebody files.
--
-- Shape: 40 aircraft in 20 pairs, each pair based at one of the 6 hubs
-- (airport_id 1-6). Odd aircraft fly 4 legs a day (hub-S1-hub-S2-hub), even
-- aircraft 6 legs (... -hub-S3-hub). Crew fly in teams of 4 covering 2 legs each;
-- the crew who fly an odd aircraft's first two legs usually move on to its even
-- partner's legs 3-4, which is what creates CREW cascade links between aircraft.
--
-- Staging tables (seed_*) are regular tables dropped at the end; MySQL can't
-- reference a TEMPORARY table twice in one statement (error 1137).
--
-- Note: MySQL requires WITH to directly precede the SELECT it feeds, so for
-- INSERT ... SELECT the WITH clause goes AFTER "INSERT INTO t (cols)".
SET SESSION cte_max_recursion_depth = 20000;

-- ============= AIRCRAFT (40) =============
-- Pair k = CEIL(n/2) is based at hub ((k-1) % 6) + 1. Every 10th is a widebody.
INSERT INTO aircraft (registration, type_id, base_airport_id, status)
WITH RECURSIVE seq AS (SELECT 1 AS n UNION ALL SELECT n + 1 FROM seq WHERE n < 40)
SELECT CONCAT('VT-A', LPAD(n, 2, '0')),
       IF(n % 10 = 0, 4, ((n - 1) % 3) + 1),
       ((CEIL(n / 2) - 1) % 6) + 1,
       'ACTIVE'
FROM seq;

-- ============= ROUTES (198) =============
-- Every hub connects to every other airport, both directions. Distance is a
-- deterministic pseudo-value (symmetric), duration = 45 min + distance / 13.
INSERT INTO route (origin_airport_id, dest_airport_id, distance_km, std_duration_min)
WITH pairs AS (
  SELECT h.airport_id AS o, x.airport_id AS d
  FROM airport h JOIN airport x ON x.airport_id <> h.airport_id
  WHERE h.airport_id <= 6
  UNION
  SELECT x.airport_id, h.airport_id
  FROM airport h JOIN airport x ON x.airport_id <> h.airport_id
  WHERE h.airport_id <= 6
),
dist AS (
  SELECT o, d, 400 + ((LEAST(o, d) * 37 + GREATEST(o, d) * 53) % 900) AS km FROM pairs
)
SELECT o, d, km, 45 + FLOOR(km / 13) FROM dist;

-- ============= SCHEDULE (7 days x 20 pairs x 10 legs = 1,400 flights) =============
CREATE TABLE seed_leg (
  aircraft_id INT, day_no INT, leg_no INT,
  origin INT, dest INT, route_id INT,
  std DATETIME, sta DATETIME,
  flight_id INT NULL, team_no INT NULL,
  PRIMARY KEY (aircraft_id, day_no, leg_no)
);

INSERT INTO seed_leg (aircraft_id, day_no, leg_no, origin, dest, route_id, std, sta)
WITH RECURSIVE
days AS (SELECT 0 AS d UNION ALL SELECT d + 1 FROM days WHERE d < 6),
ac AS (
  SELECT aircraft_id AS a, base_airport_id AS h,
         IF(aircraft_id % 2 = 1, 4, 6) AS legs,
         -- odd aircraft start 05:30, even 07:00; pairs staggered 10 min apart to spread slots
         IF(aircraft_id % 2 = 1, 330, 420) + (CEIL(aircraft_id / 2) % 4) * 10 AS start_min
  FROM aircraft
),
-- Spoke candidates per hub. rn_all numbers all 19 other airports; rn_open only
-- those without a curfew (13 per hub), used for the late S3 leg.
cand AS (
  SELECT h.airport_id AS h, x.airport_id AS x,
         ROW_NUMBER() OVER (PARTITION BY h.airport_id ORDER BY x.airport_id) AS rn_all,
         IF(x.open_time IS NULL,
            ROW_NUMBER() OVER (PARTITION BY h.airport_id, x.open_time IS NULL ORDER BY x.airport_id),
            NULL) AS rn_open
  FROM airport h JOIN airport x ON x.airport_id <> h.airport_id
  WHERE h.airport_id <= 6
),
spoke AS (
  SELECT ac.a, days.d, j.j, cand.x
  FROM ac CROSS JOIN days
  CROSS JOIN (SELECT 1 AS j UNION ALL SELECT 2 UNION ALL SELECT 3) j
  JOIN cand ON cand.h = ac.h
   AND ((j.j < 3 AND cand.rn_all = ((ac.a * 7 + days.d * 5 + j.j * 11) % 19) + 1)
     OR (j.j = 3 AND cand.rn_open = ((ac.a * 3 + days.d * 7) % 13) + 1))
),
chain AS (
  SELECT ac.a, days.d, 1 AS leg_no, ac.h, ac.legs, ac.h AS origin, s.x AS dest, r.route_id,
         CAST(DATE_ADD(TIMESTAMP(DATE_ADD(CURDATE(), INTERVAL days.d DAY)), INTERVAL ac.start_min MINUTE) AS DATETIME) AS std,
         CAST(DATE_ADD(TIMESTAMP(DATE_ADD(CURDATE(), INTERVAL days.d DAY)), INTERVAL ac.start_min + r.std_duration_min MINUTE) AS DATETIME) AS sta
  FROM ac CROSS JOIN days
  JOIN spoke s ON s.a = ac.a AND s.d = days.d AND s.j = 1
  JOIN route r ON r.origin_airport_id = ac.h AND r.dest_airport_id = s.x
  UNION ALL
  -- next leg departs after the turnaround at this leg's destination + 0-15 min slack
  SELECT c.a, c.d, c.leg_no + 1, c.h, c.legs, c.dest,
         IF((c.leg_no + 1) % 2 = 1, s.x, c.h),
         r.route_id,
         DATE_ADD(c.sta, INTERVAL ap.min_turnaround_min + ((c.a + c.d + c.leg_no) % 4) * 5 MINUTE),
         DATE_ADD(c.sta, INTERVAL ap.min_turnaround_min + ((c.a + c.d + c.leg_no) % 4) * 5 + r.std_duration_min MINUTE)
  FROM chain c
  JOIN airport ap ON ap.airport_id = c.dest
  LEFT JOIN spoke s ON s.a = c.a AND s.d = c.d AND s.j = FLOOR((c.leg_no + 2) / 2)
  JOIN route r ON r.origin_airport_id = c.dest
              AND r.dest_airport_id = IF((c.leg_no + 1) % 2 = 1, s.x, c.h)
  WHERE c.leg_no < c.legs
)
SELECT a, d, leg_no, origin, dest, route_id, std, sta FROM chain;

-- Flights. Status follows the clock: anything that should have landed already
-- is ARRIVED (on time), anything in the air is DEPARTED.
INSERT INTO flight (flight_number, route_id, aircraft_id, sched_departure, sched_arrival,
                    boarding_start, gate_close, actual_departure, actual_arrival, status)
SELECT CONCAT('AI-', 100 + (aircraft_id - 1) * 6 + leg_no),
       route_id, aircraft_id, std, sta,
       DATE_SUB(std, INTERVAL 45 MINUTE),
       DATE_SUB(std, INTERVAL 15 MINUTE),
       IF(std <= NOW(), std, NULL),
       IF(sta <= NOW(), sta, NULL),
       CASE WHEN sta <= NOW() THEN 'ARRIVED'
            WHEN std <= NOW() THEN 'DEPARTED'
            WHEN DATE_SUB(std, INTERVAL 45 MINUTE) <= NOW() THEN 'BOARDING'
            ELSE 'SCHEDULED' END
FROM seed_leg
ORDER BY std, aircraft_id;

UPDATE seed_leg s
JOIN flight f ON f.aircraft_id = s.aircraft_id AND f.sched_departure = s.std
SET s.flight_id = f.flight_id;

-- ============= GATES =============
-- Greedy assignment in departure order: take the first gate at the origin that
-- has been free for 60 min (boarding opens 45 min before departure, and the gate
-- rule needs the previous flight gone 10 min before that).
DELIMITER $$
CREATE PROCEDURE seed_assign_gates()
BEGIN
  DECLARE done INT DEFAULT 0;
  DECLARE v_fid INT;
  DECLARE v_ap INT;
  DECLARE v_std DATETIME;
  DECLARE v_gate INT;
  DECLARE cur CURSOR FOR
    SELECT f.flight_id, r.origin_airport_id, f.sched_departure
    FROM flight f JOIN route r ON r.route_id = f.route_id
    ORDER BY f.sched_departure, f.flight_id;
  DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = 1;

  CREATE TABLE seed_gate_free (gate_id INT PRIMARY KEY, airport_id INT, free_from DATETIME NULL);
  INSERT INTO seed_gate_free SELECT gate_id, airport_id, NULL FROM gate;

  OPEN cur;
  gate_loop: LOOP
    FETCH cur INTO v_fid, v_ap, v_std;
    IF done THEN LEAVE gate_loop; END IF;
    -- scalar subquery, not SELECT ... INTO: an empty SELECT INTO would fire the
    -- NOT FOUND handler and end the loop early
    SET v_gate = (SELECT gate_id FROM seed_gate_free
                  WHERE airport_id = v_ap AND (free_from IS NULL OR free_from <= v_std)
                  ORDER BY COALESCE(free_from, '1000-01-01'), gate_id LIMIT 1);
    IF v_gate IS NOT NULL THEN
      UPDATE flight SET gate_id = v_gate WHERE flight_id = v_fid;
      UPDATE seed_gate_free SET free_from = DATE_ADD(v_std, INTERVAL 60 MINUTE) WHERE gate_id = v_gate;
    END IF;
  END LOOP;
  CLOSE cur;
  DROP TABLE seed_gate_free;
END$$
DELIMITER ;

CALL seed_assign_gates();
DROP PROCEDURE seed_assign_gates;

-- ============= RUNWAY SLOTS =============
-- Tighten each airport's hourly slot limit to its real peak, so the schedule
-- fits exactly and a delayed flight moving into a peak hour gets bumped.
UPDATE airport a
JOIN (
  SELECT origin, MAX(cnt) AS peak FROM (
    SELECT r.origin_airport_id AS origin, DATE(f.sched_departure) AS dy, HOUR(f.sched_departure) AS hr, COUNT(*) AS cnt
    FROM flight f JOIN route r ON r.route_id = f.route_id
    GROUP BY r.origin_airport_id, DATE(f.sched_departure), HOUR(f.sched_departure)
  ) per_hour GROUP BY origin
) p ON p.origin = a.airport_id
SET a.runway_slots_per_hour = GREATEST(p.peak, 2);

-- ============= CREW (100 teams x 4 = 400) =============
-- Teams: odd aircraft legs 1-2 and 3-4; even aircraft legs 1-2, 3-4 (standby
-- when the partner's crew take those legs), and 5-6.
CREATE TABLE seed_team (team_no INT PRIMARY KEY, aircraft_id INT, first_leg INT);
INSERT INTO seed_team
SELECT ROW_NUMBER() OVER (ORDER BY a.aircraft_id, p.first_leg), a.aircraft_id, p.first_leg
FROM aircraft a
JOIN (SELECT 1 AS first_leg UNION ALL SELECT 3 UNION ALL SELECT 5) p
  ON p.first_leg < IF(a.aircraft_id % 2 = 1, 5, 7);

-- crew_id = (team_no - 1) * 4 + slot, relied on below (fresh DB, ids start at 1)
INSERT INTO crew (name, role, base_airport_id, hire_date)
WITH slots AS (
  SELECT 1 AS slot, 'CAPTAIN' AS role UNION ALL SELECT 2, 'FIRST_OFFICER'
  UNION ALL SELECT 3, 'PURSER' UNION ALL SELECT 4, 'CABIN_CREW'
)
SELECT
  CONCAT(
    ELT(((t.team_no * 4 + s.slot) % 24) + 1, 'Aarav','Vivaan','Aditya','Vihaan','Arjun','Sai','Reyansh','Krishna','Ishaan','Rohan','Ananya','Diya','Priya','Kavya','Meera','Nikhil','Farhan','Zoya','Tanvi','Rahul','Sneha','Kabir','Ira','Dev'),
    ' ',
    ELT(((t.team_no * 7 + s.slot * 5) % 20) + 1, 'Sharma','Verma','Iyer','Nair','Reddy','Rao','Gupta','Mehta','Joshi','Kulkarni','Menon','Pillai','Chawla','Bhatt','Desai','Khan','Das','Banerjee','Singh','Fernandes')
  ),
  s.role,
  a.base_airport_id,
  DATE_SUB(CURDATE(), INTERVAL (400 + ((t.team_no * 4 + s.slot) * 13) % 3000) DAY)
FROM seed_team t
JOIN aircraft a ON a.aircraft_id = t.aircraft_id
CROSS JOIN slots s
ORDER BY t.team_no, s.slot;

-- Certified on the aircraft type they fly; every third crew member on a second type.
INSERT INTO crew_certification (crew_id, type_id, certified_date, expiry_date)
SELECT c.crew_id, a.type_id,
       DATE_SUB(CURDATE(), INTERVAL 100 + (c.crew_id % 200) DAY),
       DATE_ADD(CURDATE(), INTERVAL 200 + (c.crew_id % 300) DAY)
FROM crew c
JOIN seed_team t ON t.team_no = FLOOR((c.crew_id - 1) / 4) + 1
JOIN aircraft a ON a.aircraft_id = t.aircraft_id
UNION ALL
SELECT c.crew_id, (a.type_id % 4) + 1,
       DATE_SUB(CURDATE(), INTERVAL 50 + (c.crew_id % 100) DAY),
       DATE_ADD(CURDATE(), INTERVAL 100 + (c.crew_id % 200) DAY)
FROM crew c
JOIN seed_team t ON t.team_no = FLOOR((c.crew_id - 1) / 4) + 1
JOIN aircraft a ON a.aircraft_id = t.aircraft_id
WHERE c.crew_id % 3 = 0;

-- Default roster: each leg flown by its own aircraft's team for that leg pair.
UPDATE seed_leg l
JOIN seed_team t ON t.aircraft_id = l.aircraft_id AND t.first_leg = 2 * FLOOR((l.leg_no - 1) / 2) + 1
SET l.team_no = t.team_no;

-- Cross-aircraft crew link: the odd aircraft's legs 1-2 crew take the even
-- partner's legs 3-4 when they land back at the hub in time (45 min crew
-- connection) and the whole day stays within 12 h first-departure-to-last-arrival.
UPDATE seed_leg e
JOIN seed_leg e3 ON e3.aircraft_id = e.aircraft_id AND e3.day_no = e.day_no AND e3.leg_no = 3
JOIN seed_leg e4 ON e4.aircraft_id = e.aircraft_id AND e4.day_no = e.day_no AND e4.leg_no = 4
JOIN seed_leg o1 ON o1.aircraft_id = e.aircraft_id - 1 AND o1.day_no = e.day_no AND o1.leg_no = 1
JOIN seed_leg o2 ON o2.aircraft_id = e.aircraft_id - 1 AND o2.day_no = e.day_no AND o2.leg_no = 2
JOIN seed_team t ON t.aircraft_id = e.aircraft_id - 1 AND t.first_leg = 1
SET e.team_no = t.team_no
WHERE e.aircraft_id % 2 = 0
  AND e.leg_no IN (3, 4)
  AND e3.std >= DATE_ADD(o2.sta, INTERVAL 45 MINUTE)
  AND TIMESTAMPDIFF(MINUTE, o1.std, e4.sta) <= 12 * 60;

INSERT INTO crew_assignment (flight_id, crew_id, role)
SELECT l.flight_id, c.crew_id, c.role
FROM seed_leg l
JOIN crew c ON c.crew_id BETWEEN (l.team_no - 1) * 4 + 1 AND l.team_no * 4;

-- ============= PASSENGERS (2,000) =============
INSERT INTO passenger (name, passport_no, email, phone, date_of_birth)
WITH RECURSIVE seq AS (SELECT 1 AS n UNION ALL SELECT n + 1 FROM seq WHERE n < 2000)
SELECT
  CONCAT(
    ELT(((n - 1) % 24) + 1, 'Aarav','Vivaan','Aditya','Vihaan','Arjun','Sai','Reyansh','Krishna','Ishaan','Rohan','Ananya','Diya','Priya','Kavya','Meera','Nikhil','Farhan','Zoya','Tanvi','Rahul','Sneha','Kabir','Ira','Dev'),
    ' ',
    ELT(((n * 7 - 1) % 20) + 1, 'Sharma','Verma','Iyer','Nair','Reddy','Rao','Gupta','Mehta','Joshi','Kulkarni','Menon','Pillai','Chawla','Bhatt','Desai','Khan','Das','Banerjee','Singh','Fernandes')
  ),
  CONCAT('P', LPAD(n, 8, '0')),
  CONCAT('passenger', n, '@example.com'),
  CONCAT('98', LPAD(10000000 + n, 8, '0')),
  DATE_SUB(CURDATE(), INTERVAL (365 * 18 + ((n * 137) % (365 * 57))) DAY)
FROM seq;

-- ============= BOOKINGS + TICKETS (~15,000) =============
-- 12,000 single-leg bookings, plus up to 1,500 two-leg connections through a
-- hub on different aircraft, with connection time between MCT and MCT + 3 h.
CREATE TABLE seed_conn (rn INT PRIMARY KEY, f1 INT, f2 INT);
INSERT INTO seed_conn
SELECT rn, f1, f2 FROM (
  SELECT l1.flight_id AS f1, l2.flight_id AS f2,
         ROW_NUMBER() OVER (ORDER BY (l1.flight_id * 31 + l2.flight_id * 17) % 1009, l1.flight_id, l2.flight_id) AS rn
  FROM seed_leg l1
  JOIN seed_leg l2 ON l2.origin = l1.dest AND l2.aircraft_id <> l1.aircraft_id AND l2.dest <> l1.origin
  JOIN airport ap ON ap.airport_id = l1.dest
  WHERE l2.std >= DATE_ADD(l1.sta, INTERVAL ap.min_connect_min MINUTE)
    AND l2.std <= DATE_ADD(l1.sta, INTERVAL ap.min_connect_min + 180 MINUTE)
) pairs
WHERE rn <= 1500;

INSERT INTO booking (pnr, passenger_id, booking_date, status)
WITH RECURSIVE seq AS (
  SELECT 1 AS n UNION ALL SELECT n + 1 FROM seq WHERE n < 12000 + (SELECT COUNT(*) FROM seed_conn)
)
SELECT CONCAT('PN', LPAD(UPPER(CONV(n, 10, 36)), 4, '0')),
       ((n * 7 - 1) % 2000) + 1,
       DATE_SUB(CURDATE(), INTERVAL (n % 60) DAY),
       CASE WHEN n % 47 = 0 THEN 'CANCELLED'
            WHEN n % 31 = 0 THEN 'CHECKED_IN'
            ELSE 'CONFIRMED' END
FROM seq;

CREATE TABLE seed_ticket (booking_id INT, flight_id INT, PRIMARY KEY (booking_id, flight_id));
INSERT INTO seed_ticket
WITH numbered AS (
  SELECT flight_id, ROW_NUMBER() OVER (ORDER BY flight_id) AS rn, COUNT(*) OVER () AS total FROM flight
)
SELECT b.booking_id, nf.flight_id
FROM booking b
JOIN numbered nf ON nf.rn = ((b.booking_id * 7919) % nf.total) + 1
WHERE b.booking_id <= 12000;

INSERT INTO seed_ticket
SELECT 12000 + c.rn, c.f1 FROM seed_conn c
UNION ALL
SELECT 12000 + c.rn, c.f2 FROM seed_conn c;

INSERT INTO ticket (booking_id, flight_id, seat_no, fare, class)
SELECT booking_id, flight_id,
       CONCAT(CEIL(seat_seq / 6), ELT(((seat_seq - 1) % 6) + 1, 'A','B','C','D','E','F')),
       CASE WHEN seat_seq <= 6 THEN 15000 + (booking_id % 5000)
            WHEN seat_seq <= 12 THEN 9000 + (booking_id % 3000)
            ELSE 4000 + (booking_id % 2000) END,
       CASE WHEN seat_seq <= 6 THEN 'BUSINESS'
            WHEN seat_seq <= 12 THEN 'PREMIUM'
            ELSE 'ECONOMY' END
FROM (
  SELECT booking_id, flight_id,
         ROW_NUMBER() OVER (PARTITION BY flight_id ORDER BY booking_id) AS seat_seq
  FROM seed_ticket
) seated;

-- ============= MAINTENANCE LOGS (1 per aircraft, in the past) =============
INSERT INTO maintenance_log (aircraft_id, maint_start, maint_end, type)
WITH RECURSIVE seq AS (SELECT 1 AS n UNION ALL SELECT n + 1 FROM seq WHERE n < 40)
SELECT n,
       DATE_SUB(NOW(), INTERVAL (n * 5 + 5) DAY),
       DATE_SUB(NOW(), INTERVAL (n * 5) DAY),
       ELT(((n - 1) % 7) + 1, 'SCHEDULED','UNSCHEDULED','A_CHECK','B_CHECK','C_CHECK','D_CHECK','LINE_MAINTENANCE')
FROM seq;

DROP TABLE seed_ticket;
DROP TABLE seed_conn;
DROP TABLE seed_team;
DROP TABLE seed_leg;
