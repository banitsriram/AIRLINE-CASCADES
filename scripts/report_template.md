# Airline Cascades: complete project context for the report

> **Purpose of this file.** This file holds everything about the Airline
> Cascades project, so that Claude (or anyone) can write the full project report
> from it alone, without opening the code. It covers the problem, design,
> database, every table and column, all SQL, the cascade algorithm, the data,
> every page and route, the front end, testing with real results, the
> development history, limitations, a report outline, and the complete source
> code in the appendices.
>
> **Generated:** {{GENERATED_AT}}, by `scripts/build_report_context.py` from the
> live project and database. Every number in the "live" sections was measured
> when this file was generated. Regenerate it after any change with
> `python scripts/build_report_context.py`.
>
> **For the report writer:** read section 17 first. It gives the report outline
> and the rules to follow, such as not inventing numbers.

---

## Contents

1. Project at a glance
2. Problem statement and motivation
3. Objectives and scope
4. Requirements (functional and non-functional)
5. Technology stack and architecture
6. Database design: ER model, relationships, constraints, normalisation
7. Table-by-table column reference (live)
8. Database programming: triggers, stored procedures, views, queries
9. The cascade engine: algorithm, rules, termination, pseudocode
10. Data generation (seed) and the live data volumes
11. Application: every page and feature, CRUD matrix, all routes
12. Front-end design system
13. Robustness to manual database changes (viva readiness)
14. Security and error handling
15. Testing and results (live)
16. Development history, challenges, limitations and future work
17. Instructions for the report writer
18. Screenshots
- Appendices: full source code (SQL, Python, templates, CSS, JS, tests, scripts, docs)

---

## 1. Project at a glance

| Item | Value |
|---|---|
| Title | **Airline Cascades: an airline delay-cascade simulator** |
| Course context | Database Management Systems (DBMS) project, CIA 3 |
| Author | Banit Sriram Ambati |
| Repository | https://github.com/banitsriram/AIRLINE-CASCADES |
| Database | MySQL 8.0+ (developed on the Homebrew MySQL build, macOS, Apple Silicon) |
| Back end | Python 3.9, Flask 3.0.0, mysql-connector-python 8.2.0, python-dotenv 1.0.0 |
| Front end | Server-rendered Jinja2 HTML, one CSS file built on the Refero "Dala" design tokens, two vanilla-JS canvas scripts (no framework, no build step) |
| Database objects | {{N_TABLES}} tables, {{N_VIEWS}} views, {{N_TRIGGERS}} triggers, {{N_ROUTINES}} stored procedures, 8 standalone report queries |
| Application | 11 Flask blueprints, {{N_ROUTES}} URL routes, {{N_TEMPLATES}} templates |
| Code size | {{LOC_TOTAL}} lines across SQL, Python, HTML, CSS and JS (breakdown in section 16.6) |
| Demo data | {{DATA_SUMMARY}} |

**In one sentence.** When one flight is delayed, the database works out every
other flight that has to move because it shares that flight's aircraft, crew,
gate or runway slot. It moves them, records why, and flags passengers who now
miss connections, crew who breach duty limits and flights that break airport
curfews.

---

## 2. Problem statement and motivation

Airline delays rarely stay on one flight. A late arrival makes the same
aircraft's next departure late. This knock-on effect is called
**reactionary delay**. The crew who arrive late are then late for their next
flight, which may be on a different aircraft. The late flight keeps its gate
occupied, so the next flight at that gate can't board. At a busy airport it may
also lose its runway departure slot. Industry reporting (e.g. EUROCONTROL's
CODA digests) routinely puts reactionary delay at roughly 40–50% of all delay
minutes in Europe.

Typical student airline databases are static CRUD systems: they store flights,
bookings and passengers. This project models the **dynamics** of an airline
network, and the interesting logic (a recursive, multi-rule propagation) runs
**inside the database**. That makes it a natural showcase for DBMS concepts:
- relational design to 3NF, with justified, controlled denormalisation
- referential integrity with deliberately chosen `ON DELETE` actions, `CHECK`
  constraints, `UNIQUE` keys and `ENUM` domains
- triggers that enforce business rules at the data layer
- stored procedures with transactions, `EXIT HANDLER`, `SIGNAL`/`RESIGNAL`,
  `WHILE` loops and `OUT` parameters
- recursive CTEs (`WITH RECURSIVE`) for graph traversal and for data generation
- window functions (`LAG`, `ROW_NUMBER`, `COUNT() OVER`) for "previous leg" and
  "rank within a slot"
- views for derived data that must never go stale
- a generated (virtual) column, a cursor-based procedure and `information_schema` introspection

## 3. Objectives and scope

**Objectives**
1. Design a normalised schema for an airline's operation: airports and their
   operating rules, gates, aircraft and types, routes, flights, crew and their
   certifications and rosters, passengers, bookings and tickets, delay notices
   and their knock-on effects.
2. Implement delay propagation in the database across four real-world links:
   aircraft rotation, crew connection, gate occupancy and runway slot capacity.
3. Record every knock-on change with its cause, so any delay can be audited end to end.
4. Derive the consequences (missed passenger connections, crew duty breaches,
   curfew risks) from views, so they are always current.
5. Provide a web application with full CRUD on every entity, a realistic
   delay-filing form, a per-delay impact report, live airport departure and
   arrival boards, reports, and a live schema and data browser.
6. Generate a realistic, internally consistent 7-day schedule so demos are
   repeatable, and prove that consistency with automated tests.
7. Make the website reflect manual changes made directly in MySQL, including
   `ALTER TABLE`, which will happen during the viva.

**In scope:** domestic Indian network (one time zone), 7-day planning horizon,
delays that push flights later, flagging of consequences.
**Out of scope:** automatic re-booking and crew re-rostering, moving flights
earlier again, user accounts and login, multiple time zones, live external
flight data. All data is fictional.

## 4. Requirements

**Functional**
- F1 Maintain airports (with curfew hours, runway slots per hour, minimum
  connection time, minimum turnaround), gates, aircraft types, aircraft,
  routes, delay categories and IATA delay codes.
- F2 Maintain flights (schedule, aircraft, gate, status, actual times,
  remarks), crew (roles, bases, certifications), crew assignments, passengers,
  bookings and tickets.
- F3 File a delay notice on a flight, with IATA code, sub-reason, minutes or a
  new ETD, phase, operational status (delayed / on hold / cancelled), gate
  change, new boarding time, aircraft swap, passengers deboarded, public
  announcement, meal voucher, compensation, rebooking, reported by and remarks.
- F4 Propagate the delay automatically through aircraft, crew, gate and slot
  links until the network is consistent, recording each change.
- F5 Show the impact of each delay: every affected flight with old and new
  times, cause and link; affected aircraft, airports and passengers; missed
  connections; duty breaches; curfew risks.
- F6 Show per-airport departure and arrival boards with scheduled vs estimated times.
- F7 Trace a flight's downstream cascade tree; find eligible replacement crew.
- F8 Book tickets transactionally; prevent double-booked seats; check in; cancel.
- F9 Prevent crew assignments that exceed the daily duty limit.
- F10 Reports: on-time performance, delay causes, load factor, crew duty
  status, aircraft utilisation.
- F11 Reset all delays for repeatable demonstrations.
- F12 Browse the live schema and every table's and view's rows.

**Non-functional**
- Integrity rules live in the database, not only in the UI.
- All SQL is parameterised; there is no SQL injection risk.
- Every change to the data or structure made directly in MySQL shows in the
  website on the next page load (section 13).
- A cascade over the whole 7-day network completes in about a second.
- Responsive down to phone width; keyboard focus visible; honours reduced-motion settings.
- Setup takes three commands; no build step.

## 5. Technology stack and architecture

```
 Browser  ── HTML (Jinja2) + style.css + constellation.js / ambient.js
    │  HTTP: GET pages, POST forms (no AJAX, no client framework)
 Flask application (app.py: app factory, error handlers, template filters)
    ├── src/routes/*     11 blueprints: dashboard, flights, delays, airports,
    │                    cascade, crew, passengers, bookings, reports, admin, schema
    ├── src/services/*   ALL SQL lives here, one module per domain
    ├── src/db.py        mysql-connector connection pool (size 10): query(),
    │                    execute(), call_proc(), call_proc_with_out()
    └── src/config.py    settings from .env (host, port, user, password, database)
    │  MySQL protocol
 MySQL 8 database "airline_cascades"
    ├── 01_schema.sql            tables, keys, constraints
    ├── 02_seed_reference.sql    airports + rules, gates, aircraft types, delay categories, IATA codes
    ├── 03_seed_operational.sql  aircraft, routes, 7-day schedule, gates, crew & rosters, passengers, bookings, tickets
    ├── 04_triggers.sql          3 triggers
    ├── 05_procedures.sql        6 stored procedures (incl. the cascade engine)
    ├── 06_views.sql             4 views
    ├── 07_seed_delays.sql       10 sample delay notices filed through the engine
    └── queries/q1–q8            standalone report queries
```

**Design rules followed throughout**
- **No ORM.** Routes never contain SQL; every `src/services/*.py` module owns
  its domain's SQL. Values are always passed as `%s` parameters. Where an
  identifier must be built dynamically (generic admin CRUD, schema browser,
  live record view), it comes from hard-coded configuration or from
  `information_schema`, is checked against the real table list, and is
  backtick-quoted.
- **Business rules live in the database** (triggers, CHECKs, procedures), so
  they hold whether data arrives through the website, the mysql client or a script.
- **Errors surface as messages, not crashes.** A trigger's `SIGNAL SQLSTATE
  '45000'` becomes a `mysql.connector.Error`. Mutating routes catch it with the
  `db_action()` helper and flash the message. Any other database error is
  rendered by a global error page that shows MySQL's exact message.
- **Derived data is computed, not stored**, except two documented denormalisations.

**Setup and run**
```
cp .env.example .env                 # set the MySQL password
pip install -r requirements.txt
bash scripts/setup_db.sh             # drops, creates and seeds the whole database
python app.py                        # http://localhost:5000
```
On macOS, port 5000 is taken by AirPlay Receiver, so the app was demonstrated
on port 5050 (`app.run(port=5050)`).

## 6. Database design

### 6.1 Entities (ER model)

The tables are organised in dependency layers; each layer references only the layers above it.

| Layer | Table | Represents |
|---|---|---|
| 1 | `airport` | An airport and its operating rules (curfew window, runway departures per hour, minimum passenger connection time, minimum aircraft turnaround) |
| 1 | `aircraft_type` | A model (A320-200, A321neo, B737-800, B777-300ER): seats, range, cruise speed |
| 1 | `delay_reason` | One of 8 delay categories: WEATHER, ATC, TECHNICAL, CREW, SECURITY, FUEL, MAINTENANCE, CASCADE |
| 2 | `gate` | A gate and terminal at an airport |
| 2 | `delay_code` | An IATA AHM 730 delay code (e.g. 41 aircraft defect, 71 departure weather), in one category |
| 2 | `route` | A directed origin → destination airport pair with distance and standard duration |
| 2 | `aircraft` | A physical aircraft (registration), its type, base and status |
| 2 | `crew` | A crew member: role (captain, first officer, purser, cabin crew), base, hire date |
| 2 | `passenger` | A passenger: name, passport, contact, date of birth |
| 3 | `flight` | One flight instance: number, route, aircraft, gate, scheduled/boarding/actual times, status, accumulated delay, and the flight whose delay caused its own (`parent_flight_id`) |
| 3 | `crew_certification` | Crew member × aircraft type, with certified and expiry dates |
| 3 | `duty_log` | A crew member's hours flown and on duty per day |
| 3 | `maintenance_log` | A maintenance event on an aircraft (generated downtime column) |
| 3 | `booking` | A reservation (PNR) by a passenger, with status |
| 4 | `crew_assignment` | Crew member × flight, with role and assigned/unassigned times (soft delete) |
| 4 | `ticket` | One seat on one flight within a booking: seat, class, fare, check-in, boarding |
| 4 | `flight_delay` | A delay notice filed on a flight: code, minutes, phase, status, operational changes, passenger care, audit fields |
| 4 | `delay_impact` | One knock-on change made by the cascade engine for a notice: affected flight, cause flight, link type, minutes added, ETD before/after, pass number |
| 4 | `cascade_candidate` | The engine's per-pass scratch table (no persistent facts) |

### 6.2 Relationships and cardinalities (for the ER diagram)

| Relationship | Cardinality | Implemented by | On delete |
|---|---|---|---|
| Airport has gates | 1 : N | `gate.airport_id` | CASCADE |
| Route departs from / arrives at an airport | N : 1 (twice) | `route.origin_airport_id`, `route.dest_airport_id`, CHECK origin ≠ destination | RESTRICT |
| Aircraft is of a type | N : 1 | `aircraft.type_id` | RESTRICT |
| Aircraft / crew based at an airport | N : 1 | `aircraft.base_airport_id`, `crew.base_airport_id` | RESTRICT |
| Delay code belongs to a category | N : 1 | `delay_code.reason_id` | RESTRICT |
| Flight flies a route | N : 1 | `flight.route_id` | RESTRICT |
| Flight is operated by an aircraft | N : 1 | `flight.aircraft_id` | RESTRICT |
| Flight departs from a gate | N : 1 (optional) | `flight.gate_id` | SET NULL |
| **Flight's delay caused by an earlier flight (recursive)** | N : 1 (optional) | `flight.parent_flight_id` → `flight.flight_id` | SET NULL |
| Crew ↔ flight (staffing) | M : N | `crew_assignment (flight_id, crew_id)` composite PK | CASCADE both |
| Crew ↔ aircraft type (certification) | M : N | `crew_certification (crew_id, type_id)` composite PK | CASCADE crew / RESTRICT type |
| Crew has daily duty totals | 1 : N | `duty_log.crew_id`, UNIQUE (crew_id, duty_date) | CASCADE |
| Aircraft has maintenance events | 1 : N | `maintenance_log.aircraft_id` | CASCADE |
| Passenger makes bookings | 1 : N | `booking.passenger_id` | RESTRICT |
| Booking holds tickets | 1 : N | `ticket.booking_id` | CASCADE |
| Ticket is for a flight | N : 1 | `ticket.flight_id`, UNIQUE (flight_id, seat_no) | RESTRICT |
| Flight has delay notices | 1 : N | `flight_delay.flight_id` | CASCADE |
| Notice uses a delay code | N : 1 | `flight_delay.code_id` | RESTRICT |
| Notice changes gate / swaps aircraft | N : 1 (optional) | `flight_delay.new_gate_id`, `.swap_aircraft_id` | SET NULL |
| Notice causes impacts | 1 : N | `delay_impact.delay_id` | CASCADE |
| Impact affects a flight / was caused by a flight | N : 1 | `delay_impact.flight_id` (CASCADE), `.cause_flight_id` (SET NULL) | |

Weak or associative entities: `crew_assignment`, `crew_certification`, `ticket`, `delay_impact`.

### 6.3 Integrity constraints

- **Domain / CHECK:** `sched_arrival > sched_departure`; route origin ≠
  destination; `expiry_date > certified_date`; `maint_end > maint_start`;
  `fare >= 0`; `seat_capacity > 0`, `max_range_km > 0`; `distance_km > 0`,
  `std_duration_min > 0`; airport `runway_slots_per_hour > 0`,
  `min_connect_min > 0`, `min_turnaround_min > 0`; curfew pairing
  `(open_time IS NULL AND close_time IS NULL) OR open_time < close_time`;
  `flight_delay.minutes >= 0`; `delay_impact.minutes_added > 0`; delay
  `resolved_at >= recorded_at`; duty hours non-negative.
- **Keys / UNIQUE:** airport IATA and ICAO codes; aircraft registration; route
  (origin, destination); aircraft type (model, manufacturer); delay reason
  (category, description); delay code IATA code; gate (airport, code); booking
  PNR; passenger passport; ticket (flight, seat); duty_log (crew, date).
- **ENUM domains:** flight status; aircraft status; crew role; booking status;
  ticket class; maintenance type; delay category; delay phase; delay
  operational status; impact link type.
- **Triggers** enforce the rules a CHECK can't express (duty limit, double seat) (section 8.1).
- **NOT NULL** on every mandatory attribute; `reported_by` is required on every delay notice.

### 6.4 Normalisation

All tables are in **3NF** (and BCNF for all practical purposes: every
determinant is a candidate key). Justifications worth quoting:
- `route` holds distance and standard duration because they are functionally
  dependent on the (origin, destination) pair, not on any flight.
- `ticket` is separate from `booking`: one booking (PNR) can span several
  flights (a connection), and seat, fare and class depend on the ticket.
- `crew_certification` and `crew_assignment` have composite keys because their
  attributes depend on the whole pair.
- **`flight_delay` deliberately does not store the delay category.** The
  category is a property of the IATA code (code → category), so storing it
  per notice would be a transitive dependency (delay → code → category). The
  category is reached through `delay_code`. An earlier iteration had
  `flight_delay.reason_id`; it was removed in review for exactly this reason.
- **Estimated times are not stored.** ETD/ETA = scheduled time +
  `delay_minutes`, computed by the view `v_flight_times`. A stored ETD would be
  a second copy of the same fact.
- **Operational flags are not stored.** Missed connections, duty breaches and
  curfew risks are views.
- `passenger.age` is not stored: it is computed with `TIMESTAMPDIFF` at query
  time. MySQL also forbids `CURDATE()` in generated columns.
- `maintenance_log.downtime_hours` is a generated VIRTUAL column, so it can't
  drift from start/end.

**Two documented denormalisations** (both written only by the database, never by application code):
1. **`flight.delay_minutes`.** Derivable as (the flight's own notices' minutes)
   + (the `delay_impact.minutes_added` it received), but it's read by every
   cascade rule in every pass, by every list and by every report. It is written
   only by `simulate_delay()` and `reset_all_delays()`, each in one transaction
   with the rows it summarises. `tests/test_cascade.py` checks the equality.
2. **`duty_log.hours_flown / hours_on_duty`.** Daily totals maintained by
   `trg_update_duty` when a flight's actual arrival is recorded, and read by
   the duty-limit trigger on every assignment.

### 6.5 Airport operating rules (live)

{{AIRPORT_RULES}}

The six hubs (DEL, BOM, BLR, MAA, CCU, HYD) are open 24 h, have 14 gates across
two terminals and longer connection and turnaround minimums.
`runway_slots_per_hour` is set by the seed to each airport's actual peak hour,
so the schedule fits exactly and a delayed flight moving into a peak hour gets
pushed to the next hour.

## 7. Table-by-table column reference (live, from `information_schema`)

{{COLUMNS}}

## 8. Database programming

### 8.1 Triggers

{{TRIGGERS_TABLE}}

| Trigger | Purpose |
|---|---|
| `trg_update_duty` (AFTER UPDATE ON flight) | When `actual_arrival` is first recorded, adds the flown hours (and +1 h on-duty allowance) to `duty_log` for every crew member still assigned (`unassigned_at IS NULL`), upserting per crew per day with `INSERT … ON DUPLICATE KEY UPDATE`. |
| `trg_check_duty_limit` (BEFORE INSERT ON crew_assignment) | Rejects the assignment with `SIGNAL SQLSTATE '45000'` if the crew member's hours on duty that day plus the new flight's scheduled hours would exceed 11. |
| `trg_no_double_seat` (BEFORE INSERT ON ticket) | Rejects a ticket for a seat already held on a CONFIRMED booking on the same flight. |

**Why the cascade is not a trigger.** An `AFTER UPDATE ON flight` trigger that
itself updates `flight` fails at runtime with MySQL **error 1442** ("Can't
update table 'flight' in stored function/trigger because it is already used by
statement which invoked this stored function/trigger"). MySQL also doesn't
support the recursive self-firing that multi-hop propagation needs. The
cascade is therefore an iterative stored procedure, called explicitly when a
delay is filed.

### 8.2 Stored procedures

{{ROUTINES_TABLE}}

| Procedure | What it does |
|---|---|
| `compute_cascade_candidates()` | Evaluates the four cascade rules against current estimated times and writes the delay each rule requires of every not-yet-departed flight into `cascade_candidate`. |
| `simulate_delay(p_flight_id, p_minutes, p_code_id, p_sub_reason, p_phase, p_ops_status, p_new_gate_id, p_new_boarding, p_pax_deboarded, p_swap_aircraft_id, p_announcement, p_meal_voucher, p_compensation, p_rebooking, p_reported_by, p_remarks, OUT p_delay_id)` | **The cascade engine.** One transaction; see section 9. |
| `reset_all_delays()` | Deletes all notices (their impacts cascade away), sets every `delay_minutes` to 0, clears `parent_flight_id`, restores cancelled flights to SCHEDULED. One transaction. |
| `analyse_cascade(p_flight_id)` | Recursive CTE over `parent_flight_id`: returns a flight's downstream delay tree with depth. |
| `find_replacement_crew(p_flight_id)` | Crew certified (unexpired) on the flight's aircraft type, based at its origin, not terminated, not on an overlapping active assignment, and under 8 duty hours that day. |
| `book_ticket(p_passenger_id, p_flight_id, p_seat_no, p_class, p_fare, OUT p_pnr)` | Transactional booking: generates a 6-character PNR from `UUID()`, inserts the booking and its first ticket, and rolls back on any error (e.g. the double-seat trigger). |

### 8.3 Views

| View | Meaning |
|---|---|
| `v_flight_times` | Every flight with STD, STA, **ETD, ETA** (scheduled + delay), gate, registration, origin/destination codes and a display status. Any status other than SCHEDULED is shown as-is; a SCHEDULED flight shows DELAYED or ON TIME. A status added to the ENUM later therefore appears without changing the view. The cascade engine itself reads this view. |
| `v_missed_connections` | Confirmed/checked-in two-ticket bookings where the onward flight (from the inbound flight's destination, within 24 h) now departs less than the connecting airport's `min_connect_min` after the inbound ETA, or was cancelled. |
| `v_duty_breaches` | Crew whose flight-duty period for a day (first ETD to last ETA over active assignments) exceeds 13 h. |
| `v_curfew_risk` | Flights whose ETD (departure side) or ETA (arrival side) falls outside the airport's opening hours. |

### 8.4 Standalone report queries (`database/queries/`)

| File | Question it answers | Techniques |
|---|---|---|
| q1_cascade_trace | Which flights did this flight's delay spread to, and at what depth? | recursive CTE |
| q2_replacement_crew | Who could replace crew on this flight? | multi-join, NOT EXISTS, correlated subquery |
| q3_ontime_performance | What share of each day's flights were within 15 min? | conditional aggregation |
| q4_top_delay_causes | Which categories cause the most delays and minutes? | join through `delay_code`, GROUP BY |
| q5_cascade_passengers | Which passengers are on the flights in a cascade? | recursive CTE + joins |
| q6_load_factor | Seats sold vs capacity per flight | LEFT JOIN to a derived table, aggregation |
| q7_duty_status | Crew nearest the duty limit today | computed columns, ordering |
| q8_aircraft_utilisation | Flights, scheduled hours and delay hours per aircraft | LEFT JOIN, aggregation |

## 9. The cascade engine

### 9.1 Definitions
- STD/STA = scheduled departure/arrival; **ETD = STD + delay_minutes**, **ETA = STA + delay_minutes**.
- A flight can be pushed only while its status is SCHEDULED or BOARDING.
  Departed or arrived flights are history, but they still act as predecessors.

### 9.2 The four rules (`compute_cascade_candidates`)

| Link | Rule for a flight B | How the "previous" flight A is found |
|---|---|---|
| **AIRCRAFT** | `required(B) = ETA(A) + min_turnaround(B's origin) − STD(B)` | `LAG(flight_id) OVER (PARTITION BY aircraft_id ORDER BY std, flight_id)` |
| **CREW** | `required(B) = ETA(A) + 45 min − STD(B)` for each active crew member | `LAG(flight_id) OVER (PARTITION BY crew_id ORDER BY std, flight_id)` over active `crew_assignment` ⋈ `v_flight_times` |
| **GATE** | `required(B) = ETD(A) + 10 min − boarding(B)`, where boarding = `boarding_start` (or STD − 45) | `LAG(flight_id) OVER (PARTITION BY gate_id ORDER BY std, flight_id)` |
| **SLOT** | if B's rank among departures in its airport-hour exceeds `runway_slots_per_hour`: `required(B) = start of next hour − STD(B)` | `ROW_NUMBER() OVER (PARTITION BY origin, DATE(etd), HOUR(etd) ORDER BY (delay>0), etd, flight_id)`, so undelayed flights keep their slots |

A rule is satisfied when `required ≤ current delay_minutes`.

### 9.3 `simulate_delay` step by step
```
START TRANSACTION   (EXIT HANDLER FOR SQLEXCEPTION → ROLLBACK; RESIGNAL)
1. Lock the flight row (SELECT … FOR UPDATE). SIGNAL an error if it doesn't
   exist or is ARRIVED / CANCELLED / DIVERTED.
2. INSERT the delay notice (category derived through delay_code); SIGNAL on an unknown code.
3. Apply it: delay_minutes += minutes; gate_id := new gate (if any);
   aircraft_id := swap aircraft (if any); status := CANCELLED if ops_status = CANCELLED.
4. Unless cancelled, loop (at most 50 passes):
     CALL compute_cascade_candidates()
     winners := for each flight, the candidate with the largest required delay
                (ROW_NUMBER() OVER (PARTITION BY flight_id ORDER BY required_delay DESC))
     INSERT INTO delay_impact the winners whose required delay > current delay
            (delay_id, flight, cause flight, link, minutes_added, old ETD, new ETD, pass)
     UPDATE flight: delay_minutes += minutes_added; parent_flight_id := cause flight
     stop when that UPDATE changed 0 rows
5. Empty cascade_candidate; COMMIT; return the notice id (OUT parameter).
```

### 9.4 Termination and correctness
- **Termination.** A flight is updated only when a rule requires *more* delay
  than it has, so `delay_minutes` never decreases, and the slot rule only
  moves flights later. With finitely many flights and a bounded schedule, a
  pass must eventually change nothing (`ROW_COUNT() = 0`). The 50-pass cap is
  a backstop, not something the logic relies on.
- **Fixed point.** When the loop ends, no rule is violated. The test re-runs
  the rules after a cascade and asserts this.
- **Consistency.** For every flight, `delay_minutes` = (its own notices) +
  (its impacts' minutes_added). This is asserted by the test.
- **Atomicity.** The whole cascade is one transaction; any error rolls back
  the notice and every change.
- **Why a regular scratch table, not TEMPORARY.** The winner selection reads
  `cascade_candidate` inside a subquery with a window function. MySQL can't
  reopen a TEMPORARY table in one statement (**error 1137**).
- **Why rules in their own procedure.** The test can call
  `compute_cascade_candidates()` directly on the untouched schedule and prove
  it's consistent.

### 9.5 What is *flagged* rather than *moved*
Passengers don't hold flights back; they miss connections
(`v_missed_connections`). Crew over the limit (`v_duty_breaches`) and curfew
breaches (`v_curfew_risk`) are flagged for a human decision.

## 10. Data generation (seed) and data volumes

The seed is pure SQL: recursive CTEs, window functions and one cursor
procedure. Its key property is **zero-delay consistency**: with no delays
filed, no cascade rule is violated, so flights move only because someone filed
a delay.

- **Airports (20):** 12 original plus 8 more Indian airports; hubs have 14 gates
  (T1/T2), spokes 6; six spokes have a night curfew.
- **Aircraft types (4), aircraft (40):** in 20 pairs; each pair based at one of
  the six hubs; every tenth aircraft a B777-300ER.
- **Routes (198):** every hub ↔ every other airport, both directions;
  deterministic pseudo-distance of 400–1,300 km; duration = 45 min + distance/13.
- **Schedule (1,400 flights over 7 days):** odd aircraft fly 4 legs a day
  (hub→S1→hub→S2→hub) from about 05:30; even aircraft fly 6 legs from about
  07:00, and their third spoke is always curfew-free. A recursive CTE chains
  each leg's departure to the previous arrival + that airport's turnaround +
  0–15 min slack. Flight numbers repeat daily (AI-101 …). Status follows the
  clock (already landed = ARRIVED, in the air = DEPARTED, within 45 min of
  departure = BOARDING).
- **Gates:** a cursor procedure (`seed_assign_gates`, dropped after use) gives
  each departure, in time order, the first gate at its origin that has been
  free for 60 min. It uses a scalar subquery rather than `SELECT … INTO`, so
  an empty result can't fire the NOT FOUND handler and end the loop early.
- **Runway slots:** each airport's limit is set to its actual peak.
- **Crew (400):** 100 teams of four (captain, first officer, purser, cabin
  crew), each covering a pair of legs. **Cross-aircraft rostering:** when
  timing allows (≥45 min connection, day ≤12 h), the crew who fly an odd
  aircraft's legs 1–2 go on to fly its even partner's legs 3–4. This is how
  delays jump between aircraft. Every crew member is certified on their
  aircraft type, and every third on a second type.
- **Passengers (2,000), bookings and tickets:** 12,000 single-leg bookings,
  plus 1,500 two-leg **connections** through a hub on different aircraft, with
  connection time between the airport's MCT and MCT + 3 h. Seats are assigned
  per flight by `ROW_NUMBER()`: the first 6 business, next 6 premium, the rest
  economy. Every 47th booking is cancelled and every 31st checked in.
- **Maintenance:** one past event per aircraft.
- **Sample delays:** 10 realistic notices (fog at DEL, ATC flow restriction,
  hydraulic fault, late crew, security alert, fuel bowser failure, bird-strike
  inspection, inbound aircraft late, destination thunderstorms, runway
  closure) filed through `simulate_delay()` itself.

### 10.1 Live row counts

{{COUNTS_TABLE}}

{{DATA_FACTS}}

## 11. Application

### 11.1 Pages and features

- **Dashboard:** a live headline (e.g. "46 flights running late"); figures for
  flights today, running late, delayed by knock-on, missed connections, crew
  over the duty limit, curfew risks, aircraft in service and confirmed
  bookings; shortcuts to all airport boards; recent delays with their knock-on
  counts; and the **interactive network map** (section 12).
- **Flights:** search by flight number, airport code or registration; filter
  by status (including "Delayed") and date; scheduled times struck through
  next to estimated times in amber; a Delay action on every upcoming flight;
  create, edit (including gate and remarks, with the gate validated to be at
  the departure airport) and delete.
- **Flight detail:** route, aircraft, gate, status, scheduled/estimated/boarding/actual
  times, total delay, knock-on source, remarks; crew list with assign
  (role dropdown) and unassign; the notices filed on it; the knock-on delay it
  received from other flights; every column of the row, live.
- **Delay form** (the core interaction):
  - **Reason:** IATA code grouped by category, sub-reason.
  - **Timing:** minutes *or* new ETD, where either fills the other and the new
    ETA is previewed; delay phase; operational status.
  - **Operations:** gate change (gates at that airport only), new boarding time
    (auto-filled), aircraft swap, passengers deboarded.
  - **Passengers:** a public announcement, auto-drafted from the inputs and
    editable; meal voucher (auto-ticked at ≥2 h); compensation (auto at ≥3 h);
    free rebooking.
  - **Audit:** reported by (required), internal remarks.
  - **Validation:** server-side validation mirrors the database rules.
- **Impact page (per delay):** minutes on the flight, other flights delayed,
  knock-on minutes, aircraft/airports/passengers affected, missed connections;
  the full notice; every knock-on change (pass, flight, route, aircraft,
  link, cause, ETD before → after, minutes added, total delay now); missed
  connections with PNR and passenger; crew duty breaches; curfew risks.
- **Delay log:** all notices, with an open-only filter and knock-on
  counts/minutes; edit the non-timing fields; mark resolved; **Reset all
  delays**, with a confirmation page.
- **Airports:** each airport's hours, slots, turnaround, MCT, gate count,
  departures today and late departures; **flight boards** for departures and
  arrivals per airport per day, with a day picker, scheduled vs estimated
  times, gate, status and a Delay action.
- **Cascade trace:** the recursive `analyse_cascade()` tree of a flight and the passengers affected.
- **Crew:** filter by role; profile with certifications (add/remove);
  eligible replacement crew for a flight; duty status.
- **Passengers:** search; create, edit (date of birth must be in the past),
  delete; profile with bookings.
- **Bookings:** filter by status; new booking via `book_ticket()`; add tickets;
  check in; cancel (soft).
- **Reports:** on-time performance, delay causes, load factor, crew duty
  status, aircraft utilisation.
- **Admin (reference data):** one generic CRUD engine for airports (including
  their timing rules), gates, aircraft types, delay reasons, IATA delay codes,
  routes, aircraft and maintenance log. It picks up columns and ENUM values
  added later (section 13).
- **Schema:** every table with exact row counts and every view; each table's
  columns, keys and foreign keys; and a paged live row browser for any table or view.

### 11.2 CRUD matrix

| Entity | Create | Read | Update | Delete |
|---|---|---|---|---|
| Flight | `/flights/new` | `/flights/`, `/flights/<id>` | `/flights/<id>/edit` | `/flights/<id>/delete` |
| Delay notice | `/flights/<id>/delay` (via `simulate_delay`) | `/delays/`, `/delays/<id>` | `/delays/<id>/edit` (non-timing fields), `/delays/<id>/resolve` | `/delays/reset` (via `reset_all_delays`) |
| Crew | `/crew/new` | `/crew/`, `/crew/<id>` | `/crew/<id>/edit` | `/crew/<id>/delete` |
| Crew certification | `/crew/<id>/certify` | crew page | remove and re-add | `/crew/<id>/certify/<type_id>/delete` |
| Crew assignment | `/flights/<id>/assign-crew` | flight page | re-assigning reactivates | `/flights/<id>/unassign-crew/<crew_id>` (soft) |
| Passenger | `/passengers/new` | `/passengers/`, `/passengers/<id>` | `/passengers/<id>/edit` | `/passengers/<id>/delete` |
| Booking | `/bookings/new` (via `book_ticket`) | `/bookings/`, `/bookings/<id>` | cancel | cancel (soft) |
| Ticket | `/bookings/<id>/ticket` | booking page | `/bookings/ticket/<id>/checkin` | with its booking |
| Airport, gate, aircraft type, delay reason, IATA code, route, aircraft, maintenance | `/admin/<entity>/new` | `/admin/<entity>/` (plus `/airports/`) | `/admin/<entity>/<id>/edit` | `/admin/<entity>/<id>/delete` |
| delay_impact, duty_log | written only by the procedure / trigger, by design | impact page, reports, schema browser | — | with their parent rows |

### 11.3 All routes (live, from the running application)

{{ROUTES}}

## 12. Front-end design system

The interface follows a Refero style reference ("DESIGN.md", derived from the
Dala website; a copy is in `docs/design-reference/DESIGN.md` and in the appendix). Its **CSS custom properties are pasted verbatim** at the top of
`static/css/style.css`, and every rule uses those token names:
- **Colours:** Void `#000000` canvas; Bone White `#ffffff` text; Ash Gray
  `#9a9a9a` and Silver Mist `#bdbdbd` secondary text; **Electric Iris
  `#8052ff`**, reserved for the single primary action per view; **Saffron
  Spark `#ffb829`**, used consistently to mean "late"; Deep Verdant `#15846e`,
  lifted to `#3ecfae` for "on time". App extensions taken from the reference's
  particle spectrum: magenta `#ff5fa2` (cancelled/destructive) and blue
  `#5aa9ff` (boarding).
- **Type:** PP Neue Montreal, with the reference's named substitute Inter
  (Google Fonts, weights 200/400/600). Headlines are weight 400 on the scale
  113 / 78 / 48 / 42 / 36 / 24 px with −0.04em tracking; body copy is 18px at
  weight **200**; the nav and labels are 14px/600 uppercase with 0.35px
  tracking; data tables use 15px/400.
- **Spacing and shape:** 6px base unit (6/12/18/24/30/36/60/96/120);
  1,280px page width; 24px radii; no cards, borders or shadows, only faint
  hairlines between table rows for legibility.
- **Components used from the reference:**
  - Navigation Bar: transparent, logo left, links centred, one violet "File a delay" pill right.
  - Primary Action Button: 14.4 × 15.96px padding.
  - Ghost Text Button.
  - Logo Lockup: a triangular mark with a violet → teal gradient.
  - Section Headline Block: an oversized headline left; an amber label with a
    live count, light body text and actions right.
  - Team Member Card: a violet role label above a crew member's name.
  - Carousel Navigation Dots: the airport board's day picker.
  - Ambient Particle Field: drifting outlined triangles behind every page.
  - Hero Constellation.
- **Hero constellation = the airline network** (`static/js/constellation.js`).
  Each of the 20 airports is a cluster of outlined triangles at its real
  latitude and longitude over India; cluster size reflects routes and
  departures, and amber reflects late departures. Triangles stream along
  routes. It's interactive: triangles push away from the cursor; hovering an
  airport draws arcs to every airport it serves (amber to late ones), speeds
  its streams, fades unconnected airports and shows a tooltip (departures
  today, running late, routes); clicking bursts the cluster and opens that
  airport's board. It runs a one-off entrance animation, supports touch and
  honours `prefers-reduced-motion`. An airport added by SQL without known
  coordinates is placed on a ring.
- **Status marks** are small triangles in the status colour. Delayed rows get
  an amber left edge. Times show the scheduled time struck through with the
  estimate in amber. Enum values display in plain words ("First officer", "On hold").
- **Responsive and accessible:** works down to 390px wide (tables scroll,
  the nav scrolls horizontally); no horizontal page overflow; visible focus
  rings; form labels on every input; motion reduced on request.

## 13. Robustness to manual database changes (viva readiness)

During the viva, examiners will change tables directly in MySQL. The website is
built so that every such change shows up on the next page load:

| Manual change | What the site does |
|---|---|
| `INSERT` / `UPDATE` / `DELETE` rows | Visible on the next page load. Nothing is cached: every page queries MySQL. The connection pool resets each session when a connection is returned, so no stale transaction snapshot is reused (verified: 25/25 fresh reads after an external UPDATE). |
| Change airport rules, e.g. `runway_slots_per_hour` | Shown on the board and used by the very next cascade. |
| `ALTER TABLE … ADD COLUMN` on any table | Every detail page (flight, crew, passenger, booking, delay notice) has an **"All N columns"** section that reads the row with `SELECT *`. Admin lists and forms add the new column automatically (marked "(new)"), with an input matched to its type, and it can be edited and saved. The Schema pages show it. |
| `ALTER TABLE … MODIFY … ENUM(…)` (new status, role, class…) | Every dropdown reads ENUM members live from `information_schema` (flight status, crew role, booking status, ticket class, delay phase and ops status, admin selects), and validation uses the same live list. A new flight status is displayed as-is by `v_flight_times`. |
| `RENAME COLUMN` | Pages that read `SELECT *` show the new name. A page whose query names the old column shows a readable error page with MySQL's exact message instead of a crash. |
| `DROP COLUMN` | Admin forms simply omit the dropped column. Other affected pages show the readable error page. |
| New table or `CREATE VIEW` | Listed on the Schema page, with structure and a paged row browser. |
| New airport inserted by SQL | Appears on Airports, the dashboard map and board shortcuts. |
| Row counts after bulk inserts | Exact `COUNT(*)`, not InnoDB's cached `table_rows` estimate, which can lag for up to 24 h (`information_schema_stats_expiry`). |

**Caveats to state in the viva**
- If the examiner's client has autocommit off (e.g. some MySQL Workbench
  settings), changes appear only after they `COMMIT`.
- Inserting into `flight_delay` directly (bypassing `simulate_delay`) records
  a notice but doesn't move any flight or update `delay_minutes`. That's by
  design, because the cascade runs only through the procedure. Updating
  `flight.delay_minutes` directly does show everywhere immediately.

`tests/test_live_changes.py` simulates all of the above against a separate
MySQL client session (results in section 15).

## 14. Security and error handling

- Every value in SQL is a bound parameter (`%s`). Dynamic identifiers come only
  from configuration or `information_schema`, are checked against the real
  list of tables, and are backtick-quoted (with backticks doubled). There is no
  string-built SQL from user input.
- Jinja2 auto-escapes all output (no XSS through data); the map's JSON data is
  embedded with the `tojson` filter.
- Database credentials live in `.env`, which is git-ignored. `.env.example`
  documents the variables.
- Input validation happens at both layers: the forms (required fields, types,
  date of birth in the past, gate at the departure airport, delay 0–24 h) and
  the database (CHECK, ENUM, FK, triggers, procedure SIGNALs).
- **Error handling:**
  - Mutating actions catch database errors and flash them (e.g. "Assignment
    would exceed 11-hour daily duty limit", "Seat already booked on this
    flight", "Cannot delay a flight that has arrived…").
  - Any other database error renders an error page with the MySQL error
    number and message.
  - Unknown URLs render a 404 page.
- **Limitations:** no authentication or authorisation (single-operator demo);
  no CSRF tokens on forms; runs on Flask's development server.

## 15. Testing and results (live)

### 15.1 Test suite

| Test | What it proves |
|---|---|
| `tests/test_cascade.py` | (1) With zero delays, `compute_cascade_candidates()` finds no rule violations and all three flag views are empty. (2) A 180-min delay on a flight whose crew continue on another aircraft and which carries connecting passengers moves the same aircraft's later legs (AIRCRAFT), a flight on a different aircraft (CREW) and breaks ≥1 connection. (3) Every flight's `delay_minutes` = its own notices + its knock-on. (4) After the cascade no rule is violated. (5) `reset_all_delays()` returns the whole network to schedule. |
| `tests/test_crew_assignment.py` | Soft-unassigned crew can be re-assigned (no duplicate-key error) and don't accrue duty hours when the flight lands. Written for a real bug and verified to fail on the old code. |
| `tests/test_live_changes.py` | An examiner's manual changes (INSERT, UPDATE, DELETE, ADD COLUMN, ENUM change, new view, new airport, RENAME COLUMN) all show on the site (section 13). |
| Route smoke test (in the generator) | Every GET route, every admin entity page and every schema table/view page responds without a server error. |

### 15.2 Results

{{TEST_RESULTS}}

### 15.3 A worked cascade (measured just now on a fresh database)

{{DEMO_CASCADE}}

### 15.4 Sample delays in the seeded database

{{SAMPLE_DELAYS}}

### 15.5 Report query outputs (seeded database)

{{QUERY_RESULTS}}

## 16. Development history, challenges, limitations and future work

### 16.1 How the project was built (iterations)

{{GIT_LOG}}

The iterations were:
1. **Database layer:** schema, seeds, triggers and the first procedures (initial commit).
2. **Application layer:** nine Flask blueprints, services, templates and docs,
   verified end to end against a live MySQL.
3. **Completion review:** fixed soft-deleted crew assignments being counted
   (re-assign, duty trigger, replacement search), the duty-limit trigger's NULL
   bug and the README counts; added the first regression test.
4. **Organisation-wide cascade:** after a written design spec and review, added
   airport operating rules, gates, IATA delay codes, full delay notices,
   `delay_impact`, the four-rule engine, flag views, the medium-size
   consistent seed, the delay form, impact page, delay log, airport boards and
   tests. The 3NF violation `flight_delay.reason_id` was found and removed.
5. **Front end:** a redesign to the Refero/Dala dark design system: the network
   constellation and its cursor interactivity, then an exact token-level
   rebuild (verbatim CSS variables, headline blocks, team card, carousel dots,
   ambient field).
6. **Viva hardening:** live ENUMs, live admin columns, live all-columns record
   views, exact row counts, the schema row browser, readable error pages and
   the manual-change test.

### 16.2 Key decisions and why they were made

| Decision | Options considered | Chosen | Reason |
|---|---|---|---|
| Database engine | Port everything to **Oracle** (PL/SQL, sequences, `oracledb` driver, Oracle Free in Docker); keep MySQL and also write Oracle-equivalent scripts; stay on MySQL | **Stay on MySQL 8** | The whole schema, the seven SQL files and every query already worked on MySQL. An Oracle port meant rewriting about 700 lines of SQL (AUTO_INCREMENT → sequences/identity, ENUM → CHECK, `ON DUPLICATE KEY` → MERGE, `TIMESTAMPDIFF`/`DATE_ADD` → interval arithmetic, `LIMIT` → `FETCH FIRST`) and every Flask query, plus running a 2–3 GB container. The author chose to keep MySQL and put the effort into features. An Oracle port is listed as future work. |
| Where the cascade logic lives | Trigger; Python in the app; stored procedure | **Iterative stored procedure** | A self-updating trigger is impossible in MySQL (error 1442). Python would move the core logic out of the DBMS, the subject being examined. A procedure keeps it in the database, atomic and testable. |
| Which links carry a delay | Aircraft only (the original design); + crew; + passenger connections; + airport slots and gates | **All four**, with passengers flagged rather than holding flights | This matches how airlines actually propagate delay. Passengers don't hold aircraft in practice; they miss connections. |
| Delay form contents | Core notice; operational extras; passenger-facing; audit | **All four groups** | A realistic duty-manager notice (IATA code, phase, ETD, gate change, swap, announcement, meal voucher, compensation, reporter). |
| Data size | Keep 300 flights; medium (~1,400 flights / 7 days); large (~4,000 / 14 days) | **Medium** | Big enough for delays to spread across the network; loads in seconds; cascades run in about a second. |
| Estimated times | Store ETD/ETA columns; derive them | **Derive in a view** | Storing them would duplicate `delay_minutes` and could drift. |
| Flags (missed connections, duty, curfew) | Store as columns or tables; views | **Views** | Always current; nothing to keep in sync. |
| Delay category on a notice | Store `reason_id` on `flight_delay`; derive through `delay_code` | **Derive** | Storing it would be a transitive dependency (3NF). |
| Tailwind CSS for the redesign | Tailwind via CDN; compiled Tailwind; exact CSS custom properties | **Exact CSS custom properties** | The same tokens as the reference's `@theme` block, but with no internet dependency during the viva and no build step. |
| Handling hand-edited tables | Fixed templates; introspect `information_schema` | **Introspect** | Examiners will ALTER tables live; the site must show new columns, ENUM values and views without code changes. |

### 16.3 Challenges and how they were solved

1. **MySQL error 1442:** a trigger can't update its own table, so the cascade
   became an explicit iterative procedure.
2. **MySQL error 1137:** a TEMPORARY table can't be reopened in one statement,
   so the scratch table is a regular table, emptied per pass.
3. **Errors 3763/3814/3823:** no `CURDATE()` in generated columns or CHECKs, and
   no CHECK on a column with an FK referential action. Age is computed at
   query time, date of birth is validated in the app, and the self-parent
   CHECK was dropped because the engine guarantees it.
4. **MD5/SHA1 unavailable** on OpenSSL-3 MySQL builds, so PNRs come from `UUID()`.
5. **Soft-deleted crew assignments counted as active** in three places; fixed,
   with a regression test.
6. **`SELECT … INTO` with no row leaves the variable NULL:** the duty trigger
   never fired for a crew member's first assignment. Fixed with `DEFAULT 0`.
7. **Cursor NOT FOUND handler ended the loop early** when an inner `SELECT … INTO`
   found nothing; the seed uses a scalar subquery instead.
8. **Making the seed consistent with all four rules at once** (turnarounds,
   45-min crew connections, a 55-min gate gap, slot peaks, curfews, 12-h crew
   days). Solved by construction and proven by test.
9. **A transitive dependency** (`flight_delay.reason_id`) caught in review and removed.
10. **Stale counts and hard-coded structure** would have hidden examiners'
    changes; fixed by introspecting `information_schema`.
11. **Front-end details:** an animation timestamp quirk stalled the map's
    entrance in some browsers (fixed by using `performance.now()`); tabular
    figures spread hyphens in "AI-101" (scoped to time cells only).

### 16.4 Limitations
- Delays only move flights later. Resolving a notice doesn't pull flights
  back; reset is all-or-nothing, and gate changes and aircraft swaps aren't
  reverted by reset (`setup_db.sh` rebuilds everything).
- Crew connection (45 min) and the flight-duty limit (13 h) are constants.
- Missed connections, duty breaches and curfews are flagged; there is no
  automatic re-booking, re-rostering or cancellation.
- Single time zone; multi-timezone would need UTC storage.
- Demo load factors are low (about 5–6%), because connection coverage was prioritised.
- No authentication; development server only.

### 16.5 Future work
An Oracle PL/SQL port; optimisation (choose which flights to delay, swap or
cancel to minimise total passenger delay); automatic re-booking of missed
connections; crew re-rostering; resolving delays to pull flights earlier;
multi-timezone support; role-based access; real-time updates via websockets;
analytics of reactionary vs primary delay over time; delay prediction.

### 16.6 Code size by file

{{LOC_TABLE}}

## 17. Instructions for the report writer

Write a formal DBMS project report from this file.
- Use only facts stated here. Don't invent numbers, features, results,
  references or people.
- Leave the college, department, register number, guide name, dates and
  signatures as clearly marked placeholders.
- Keep code excerpts short in the body (the key parts of the schema, one
  trigger, the cascade rules, one view) and put full listings in the appendix.
- Refer to screenshots by their file names (section 18) so the author can insert them.

**Suggested structure**
1. Title page: *Airline Cascades: An Airline Delay-Cascade Simulator*. DBMS Project (CIA 3). Banit Sriram Ambati. Placeholders for the rest.
2. Certificate / declaration / acknowledgement (placeholders).
3. Abstract (150–250 words): problem; approach (in-database iterative cascade
   over four link types, with consequences derived by views); stack; key
   results from sections 15.3–15.4 (engine time, flights moved, the
   reactionary-to-primary ratio).
4. Table of contents; list of figures; list of tables.
5. Introduction: reactionary delay; why this is a database problem; objectives (section 3).
6. Literature and background: reactionary delay (EUROCONTROL CODA); IATA
   delay codes (AHM 730); relational model and normalisation (Codd); MySQL
   triggers, stored programs, recursive CTEs and window functions.
7. Requirements analysis (section 4), with a hardware/software table
   (MySQL 8+, Python 3.9+, Flask 3, any OS).
8. System design: architecture (section 5); the **ER diagram** (draw it from
   sections 6.1–6.2 with attributes from section 7); relational schema;
   constraints (6.3); normalisation (6.4).
9. Implementation: DDL, triggers (8.1), procedures (8.2), views (8.3), queries
   (8.4), the cascade engine with pseudocode and a flowchart (section 9), data
   generation (10), application modules and pages (11), front end (12),
   robustness to manual changes (13), security (14).
10. Testing: test cases as a table (ID, description, input/steps, expected,
    actual, status), built from sections 15.1–15.2 and 13.
11. Results and discussion: the worked cascade (15.3) with a propagation
    diagram; sample delays and the reactionary ratio (15.4); report outputs
    (15.5); screenshots.
12. Key decisions (16.2) and challenges faced (16.3).
13. Limitations and future scope (16.4–16.5).
14. Conclusion.
15. References (below).
16. Appendices: SQL listings (Appendix A), selected application code (B),
    column reference (section 7), route list (11.3).

**Diagrams to produce**
- ER diagram (entities, attributes, PKs/FKs, cardinalities, the recursive `parent_flight_id`).
- Architecture/layer diagram (section 5).
- `simulate_delay` flowchart (9.3).
- Propagation graph of the worked example (15.3): nodes are flights, edges labelled with the link type.
- Optionally a DFD level 0/1: Duty manager → File delay → Cascade engine → Impact / boards / flags.

**References to use**
1. Oracle. *MySQL 8.0 Reference Manual*: Triggers; Stored Programs; `WITH` (Common Table Expressions); Window Functions; `information_schema`. https://dev.mysql.com/doc/refman/8.0/en/
2. IATA. *Airport Handling Manual (AHM 730): Standard Delay Codes*.
3. EUROCONTROL. *CODA Digest: All-causes delay and cancellations to air transport in Europe* (annual/quarterly).
4. E. F. Codd, "A Relational Model of Data for Large Shared Data Banks," *Communications of the ACM*, 13(6), 1970.
5. R. Elmasri and S. B. Navathe, *Fundamentals of Database Systems*, Pearson.
6. A. Silberschatz, H. F. Korth and S. Sudarshan, *Database System Concepts*, McGraw-Hill.
7. Pallets Projects. *Flask documentation*. https://flask.palletsprojects.com/
8. Refero. *Dala style reference (DESIGN.md)*, used for the interface design system.

## 18. Screenshots

The screenshots are in `docs/screenshots/`, captured at 1440×900 (and 390×844 for mobile):

{{SCREENSHOTS}}

---

# Appendices: complete source code

Everything below is the project's source as it was when this file was
generated. `.env` (credentials) is deliberately excluded. Other docs in the
repository are included at the end.

{{SOURCE}}
