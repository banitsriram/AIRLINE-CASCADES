# Organisation-wide delay cascade — design

Date: 2026-09-23 · Status: approved in chat, awaiting spec review

## Goal

Make the app interactive for the DBMS project demo: the user files a realistic
delay on any flight, and the delay propagates across the whole airline —
aircraft, crew, gates, runway slots — with every changed timing visible, plus
missed passenger connections, duty-limit and curfew flags. All inputs are typed
by the user; data is fake.

## Decisions (from the user)

| Topic | Decision |
|---|---|
| Database | Stay on MySQL 8 (Oracle port judged not worth the rewrite). |
| Cascade links | Aircraft rotation, crew connections, passenger connections, airport slots & gates — all four. |
| Delay form | Core notice + operational extras + passenger-facing + audit fields (all four groups). |
| Data size | Medium: 20 airports, 40 aircraft, ~1,500 flights / 7 days, 120 crew, 2,000 passengers, ~15,000 tickets. |
| Engine | Approach A: iterative stored procedure in the DB, every knock-on change logged to a table. |

## Principles

- **Estimated times are derived, not stored.** `ETD = sched_departure + delay_minutes`,
  `ETA = sched_arrival + delay_minutes`. `delay_minutes` stays the single
  maintained denormalization on `flight`.
- **Flags are views, not columns.** Missed connections, duty breaches and
  curfew risk are computed by views over current ETD/ETA, so they can never go
  stale.
- **Zero-delay consistency.** Freshly seeded data must satisfy every cascade
  rule with all delays at 0, so a cascade only ever moves flights because of a
  filed delay. This is a tested invariant.

## 1. Data model

### Changed tables

**`airport`** — add:
- `open_time TIME`, `close_time TIME` — curfew window (NULL/NULL = 24h).
- `runway_slots_per_hour INT NOT NULL` (CHECK > 0) — max departures per clock hour.
- `min_connect_min INT NOT NULL` — minimum passenger connection time.
- `min_turnaround_min INT NOT NULL` — minimum aircraft turnaround.

**`flight`** — add:
- `gate_id INT NULL` → `gate(gate_id)` `ON DELETE SET NULL` (departure gate).
- `remarks VARCHAR(200) NULL`.

Display status (ON TIME / DELAYED / BOARDING / DEPARTED / ARRIVED /
CANCELLED) is derived from `status` + `delay_minutes`; no new status column.

**`flight_delay`** — keep existing columns, add the notice fields:

| Group | Columns |
|---|---|
| Core | `code_id` → `delay_code`, `sub_reason VARCHAR(200)`, `phase ENUM('PRE_BOARDING','AT_GATE','TAXI','AIRBORNE')` |
| Operational | `new_gate_id` → `gate`, `new_boarding_time DATETIME`, `pax_deboarded BOOL`, `swap_aircraft_id` → `aircraft` (NULL = no swap), `ops_status ENUM('DELAYED','ON_HOLD','CANCELLED')` |
| Passenger-facing | `announcement VARCHAR(500)`, `meal_voucher BOOL`, `compensation_eligible BOOL`, `rebooking_offered BOOL` |
| Audit | `reported_by VARCHAR(80) NOT NULL`, `remarks VARCHAR(500)`; existing `recorded_at` = reported at, `resolved_at` = resolve action |

`meal_voucher` / `compensation_eligible` default from minutes (≥ 120 / ≥ 180)
in the form but are user-editable.

### New tables

- **`gate`** — `gate_id`, `airport_id` → `airport` (CASCADE), `gate_code`,
  `terminal`; `UNIQUE (airport_id, gate_code)`.
- **`delay_code`** — `code_id`, `iata_code CHAR(2) UNIQUE`, `description`,
  `reason_id` → `delay_reason`. Seeded with ~20 real IATA codes (e.g. 41
  aircraft defect, 63 late crew boarding, 71 departure weather, 81 ATC en-route,
  93 aircraft rotation) mapped to the 8 existing categories.
- **`delay_impact`** — one row per knock-on change:
  `impact_id`, `delay_id` → `flight_delay` (CASCADE), `flight_id` → `flight`,
  `cause_flight_id` → `flight`, `link ENUM('AIRCRAFT','CREW','GATE','SLOT')`,
  `minutes_added INT` (CHECK > 0), `old_etd DATETIME`, `new_etd DATETIME`,
  `pass_no INT`.

### New views

- **`v_flight_times`** — every flight with STD, STA, ETD, ETA, gate, derived
  display status.
- **`v_missed_connections`** — pairs of tickets in the same CONFIRMED booking
  where flight 1's destination = flight 2's origin, flight 2 departs after
  flight 1, and `ETD2 − ETA1 < airport.min_connect_min` of the connecting
  airport.
- **`v_duty_breaches`** — crew whose summed scheduled-block hours on active
  assignments for a duty day, measured on ETD/ETA, exceed 11 h.
- **`v_curfew_risk`** — flights whose ETD or ETA falls outside the respective
  airport's `open_time`–`close_time`.

## 2. Cascade engine — `simulate_delay()`

New signature (one call from the delay form):
`simulate_delay(p_flight_id, p_minutes, p_code_id, ...notice fields..., OUT p_delay_id)`.

Steps, in one transaction (EXIT HANDLER → ROLLBACK + RESIGNAL, like
`book_ticket()`):

1. Insert the `flight_delay` notice.
2. Apply the notice to the flight: `delay_minutes += p_minutes`; if
   `new_gate_id` → set `gate_id`; if `swap_aircraft_id` → set `aircraft_id`;
   if `ops_status = 'CANCELLED'` → `status = 'CANCELLED'` and stop (a cancelled
   flight does not propagate).
3. Loop until a pass changes no flight (cap 50 passes). Each pass computes, for
   every non-cancelled flight, the minimum delay each rule requires; takes the
   max per flight; and for flights whose required delay exceeds current
   `delay_minutes` writes one `delay_impact` row (the winning rule and cause
   flight) and raises `delay_minutes`. Rules:
   - **AIRCRAFT** — for consecutive flights A→B of the same aircraft (by STD):
     `ETD(B) ≥ ETA(A) + min_turnaround_min` of B's origin.
   - **CREW** — for each active crew assignment on B, with A the crew member's
     previous active assignment (by STD): `ETD(B) ≥ ETA(A) + 45`.
   - **GATE** — for consecutive flights A→B at the same departure gate:
     `boarding(B) ≥ ETD(A) + 10`, where `boarding = boarding_start + delay`
     (or `STD − 45` when `boarding_start` is NULL).
   - **SLOT** — rank departures per (origin airport, clock hour of ETD) with
     `ROW_NUMBER()` ordering undelayed flights first, then by ETD; ranks beyond
     `runway_slots_per_hour` move to the start of the next hour.

   `delay_minutes` only increases and the slot rule only moves flights later,
   so the loop terminates; the cap is a backstop. Candidate rows per pass go
   through a regular (non-TEMPORARY) scratch table, because MySQL can't
   reference a TEMPORARY table twice in one statement (error 1137).
4. Return `p_delay_id`.

Passenger connections, duty breaches and curfew risk are **not** rules that
move flights — they are read from the views after the cascade.

**`reset_all_delays()`** — new procedure for repeatable demos: deletes
`delay_impact` and `flight_delay` rows, sets `delay_minutes = 0`,
`parent_flight_id = NULL`, restores `status` from `CANCELLED` to `SCHEDULED`.
Aircraft swaps and gate changes are **not** undone (the flight's original
values aren't kept); re-run `scripts/setup_db.sh` for a full reset.

**`parent_flight_id`** is kept and set to the cause flight of the most recent
impact, so the existing `analyse_cascade()` recursive CTE and cascade trace
page keep working.

**`resolve_delay(p_delay_id)`** — sets `resolved_at = NOW()`; informational
only (does not pull flights earlier).

## 3. UI

- **Delay button** on each row of `/flights/` and on `/flights/<id>` →
  `GET/POST /flights/<id>/delay`. Form groups: Core, Operational,
  Passenger-facing, Audit. Minutes and new ETD are linked: editing one updates
  the other (a small inline `<script>`); the server recomputes minutes from ETD
  as the source of truth. Code dropdown is grouped by category.
- **Impact page** `GET /delays/<delay_id>` — the notice, then a table of
  every affected flight: flight, link, cause flight, old ETD → new ETD,
  +minutes; then missed connections, duty breaches and curfew risks involving
  affected flights. Redirected to after filing.
- **Delay list** `GET /delays/` — all notices, newest first, with resolve
  action; **edit** `GET/POST /delays/<id>/edit` changes only non-timing fields
  (announcement, remarks, flags, reported_by). Changing minutes = file another
  delay.
- **Airport board** `GET /airports/<id>/board?date=` — departures and arrivals
  for a day: STD/ETD, STA/ETA, gate, display status, remarks; changed times
  highlighted. Linked from the dashboard and admin airport list.
- **Reset all delays** button (with confirm page, not a JS dialog) on the
  cascade index.
- **Admin CRUD** gains `gate` and `delay_code`; the airport entity gains the
  new timing columns; the flight form gains gate + remarks.

## 4. Seed data (medium)

Generated in SQL with recursive CTEs, like the existing seeds:

- 20 airports (12 existing + 8 more Indian airports), 4–12 gates each by size,
  hubs (DEL, BOM, BLR) with more gates and slots, some airports with a
  night curfew.
- 40 aircraft; each flies a daily rotation of 4–6 legs from its base, with
  ground time ≥ `min_turnaround_min` of the turnaround airport.
- ~1,500 flights over 7 days; gates assigned so consecutive flights at a gate
  are ≥ 60 min apart; hourly departures within slot limits.
- 120 crew as 2-pilot + cabin teams; most teams follow one aircraft for a day,
  but some cabin crew switch aircraft at a hub mid-day so CREW links appear
  independently of AIRCRAFT links.
- 2,000 passengers; ~15,000 tickets, ~15% of bookings are two-leg connections
  through a hub with connection time between MCT and MCT + 3 h.
- ~40 pre-existing delays with impacts, so reports have data.

The zero-delay-consistency invariant is checked by the test below.

## 5. Testing

- `tests/test_cascade.py` (assert-based, runs on a freshly seeded DB):
  1. With all delays 0, no rule is violated (every rule's required delay ≤ 0).
  2. A 180-minute delay on the first leg of a chosen rotation moves that
     aircraft's later legs (AIRCRAFT impacts), at least one flight on a
     different aircraft (CREW impact), and produces ≥ 1 row in
     `v_missed_connections`.
  3. Every flight's `delay_minutes` equals the filed delay plus its impacts'
     `minutes_added`.
  4. `reset_all_delays()` returns every flight to `delay_minutes = 0`.
- Existing `tests/test_crew_assignment.py` keeps passing.
- Smoke test: every GET route returns < 400.

## 6. Docs

Update `README.md` (counts), `docs/CRUD_MATRIX.md` (gate, delay_code, delay
notice), `docs/DEVIATIONS.md` (scratch table vs TEMPORARY), `docs/VIVA_PREP.md`
(how the cascade engine works), `docs/SCHEMA_DIAGRAM.md` (new tables),
`docs/NORMALIZATION.md` (new tables; derived ETD/ETA).

## Out of scope

- Oracle port.
- Auto-cancellation / curfew enforcement (flagged only).
- Automatic rebooking of missed connections (flagged only).
- Pulling flights earlier when a delay is resolved.
- Real-time updates / websockets; pages reload.
