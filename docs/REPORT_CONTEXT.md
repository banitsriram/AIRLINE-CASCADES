# Airline Cascades: complete project context for the report

> **Purpose of this file.** This file holds everything about the Airline
> Cascades project, so that Claude (or anyone) can write the full project report
> from it alone, without opening the code. It covers the problem, design,
> database, every table and column, all SQL, the cascade algorithm, the data,
> every page and route, the front end, testing with real results, the
> development history, limitations, a report outline, and the complete source
> code in the appendices.
>
> **Generated:** Wednesday 23 September 2026, 16:38, by `scripts/build_report_context.py` from the
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
| Database objects | 19 tables, 4 views, 3 triggers, 6 stored procedures, 8 standalone report queries |
| Application | 11 Flask blueprints, 52 URL routes, 40 templates |
| Code size | 6,360 lines across SQL, Python, HTML, CSS and JS (breakdown in section 16.6) |
| Demo data | 20 airports, 168 gates, 40 aircraft, 198 routes, 1,400 flights over 7 days, 400 crew, 2,000 passengers, 13,500 bookings, 15,000 tickets, 31 IATA delay codes |

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

| IATA | ICAO | City | Hours | Departures/hour | Min connection (min) | Min turnaround (min) | Gates |
|---|---|---|---|---|---|---|---|
| DEL | VIDP | Delhi | 24 h | 5 | 75 | 60 | 14 |
| BOM | VABB | Mumbai | 24 h | 5 | 75 | 60 | 14 |
| BLR | VOBL | Bengaluru | 24 h | 3 | 60 | 55 | 14 |
| MAA | VOMM | Chennai | 24 h | 4 | 60 | 50 | 14 |
| CCU | VECC | Kolkata | 24 h | 4 | 60 | 50 | 14 |
| HYD | VOHS | Hyderabad | 24 h | 3 | 60 | 50 | 14 |
| PNQ | VAPO | Pune | 06:00–23:00 | 2 | 45 | 45 | 6 |
| GOI | VOGO | Goa | 06:00–23:30 | 2 | 45 | 45 | 6 |
| AMD | VAAH | Ahmedabad | 24 h | 2 | 45 | 45 | 6 |
| COK | VOCI | Kochi | 24 h | 2 | 45 | 45 | 6 |
| LKO | VILK | Lucknow | 24 h | 2 | 45 | 45 | 6 |
| JAI | VIJP | Jaipur | 24 h | 2 | 45 | 45 | 6 |
| TRV | VOTV | Thiruvananthapuram | 24 h | 2 | 45 | 45 | 6 |
| IXC | VICG | Chandigarh | 06:00–22:30 | 2 | 45 | 45 | 6 |
| PAT | VEPT | Patna | 06:00–22:30 | 2 | 45 | 45 | 6 |
| BBI | VEBS | Bhubaneswar | 24 h | 2 | 45 | 45 | 6 |
| GAU | VEGT | Guwahati | 24 h | 2 | 45 | 45 | 6 |
| NAG | VANP | Nagpur | 24 h | 2 | 45 | 45 | 6 |
| IXB | VEBD | Bagdogra | 06:00–21:30 | 2 | 45 | 45 | 6 |
| VNS | VEBN | Varanasi | 06:00–22:30 | 2 | 45 | 45 | 6 |

The six hubs (DEL, BOM, BLR, MAA, CCU, HYD) are open 24 h, have 14 gates across
two terminals and longer connection and turnaround minimums.
`runway_slots_per_hour` is set by the seed to each airport's actual peak hour,
so the schedule fits exactly and a delayed flight moving into a peak hour gets
pushed to the next hour.

## 7. Table-by-table column reference (live, from `information_schema`)

#### `aircraft` (table, 40 rows)

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `aircraft_id` | `int` | NO | PRI | auto_increment |
| `registration` | `varchar(10)` | NO | UNI |  |
| `type_id` | `int` | NO | MUL | FK → `aircraft_type.type_id` |
| `base_airport_id` | `int` | NO | MUL | FK → `airport.airport_id` |
| `status` | `enum('ACTIVE','MAINTENANCE','GROUNDED','RETIRED')` | NO |  | default `ACTIVE` |
| `created_at` | `timestamp` | NO |  | default `CURRENT_TIMESTAMP` |
| `retired_at` | `timestamp` | YES |  |  |

#### `aircraft_type` (table, 4 rows)

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `type_id` | `int` | NO | PRI | auto_increment |
| `model` | `varchar(40)` | NO | MUL |  |
| `manufacturer` | `varchar(40)` | NO |  |  |
| `seat_capacity` | `int` | NO |  |  |
| `max_range_km` | `int` | NO |  |  |
| `cruise_speed_kmh` | `int` | YES |  |  |
| `created_at` | `timestamp` | NO |  | default `CURRENT_TIMESTAMP` |

#### `airport` (table, 20 rows)

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `airport_id` | `int` | NO | PRI | auto_increment |
| `iata_code` | `char(3)` | NO | UNI |  |
| `icao_code` | `char(4)` | YES | UNI |  |
| `city` | `varchar(60)` | NO |  |  |
| `country` | `varchar(60)` | NO |  |  |
| `timezone` | `varchar(40)` | NO |  |  |
| `open_time` | `time` | YES |  |  |
| `close_time` | `time` | YES |  |  |
| `runway_slots_per_hour` | `int` | NO |  | default `6` |
| `min_connect_min` | `int` | NO |  | default `60` |
| `min_turnaround_min` | `int` | NO |  | default `45` |
| `created_at` | `timestamp` | NO |  | default `CURRENT_TIMESTAMP` |

#### `booking` (table, 13,500 rows)

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `booking_id` | `int` | NO | PRI | auto_increment |
| `pnr` | `char(6)` | NO | UNI |  |
| `passenger_id` | `int` | NO | MUL | FK → `passenger.passenger_id` |
| `booking_date` | `date` | NO |  | default `curdate()` |
| `status` | `enum('CONFIRMED','CANCELLED','CHECKED_IN','COMPLETED')` | NO |  | default `CONFIRMED` |
| `cancelled_at` | `timestamp` | YES |  |  |
| `created_at` | `timestamp` | NO |  | default `CURRENT_TIMESTAMP` |
| `updated_at` | `timestamp` | NO |  | on update CURRENT_TIMESTAMP; default `CURRENT_TIMESTAMP` |

#### `cascade_candidate` (table, 0 rows)

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `flight_id` | `int` | NO | MUL |  |
| `cause_flight_id` | `int` | YES |  |  |
| `link` | `enum('AIRCRAFT','CREW','GATE','SLOT')` | NO |  |  |
| `required_delay` | `int` | NO |  |  |

#### `crew` (table, 400 rows)

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `crew_id` | `int` | NO | PRI | auto_increment |
| `name` | `varchar(80)` | NO |  |  |
| `role` | `enum('CAPTAIN','FIRST_OFFICER','CABIN_CREW','PURSER')` | NO |  |  |
| `base_airport_id` | `int` | NO | MUL | FK → `airport.airport_id` |
| `hire_date` | `date` | NO |  |  |
| `terminated_at` | `timestamp` | YES |  |  |
| `created_at` | `timestamp` | NO |  | default `CURRENT_TIMESTAMP` |

#### `crew_assignment` (table, 5,600 rows)

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `flight_id` | `int` | NO | PRI | FK → `flight.flight_id` |
| `crew_id` | `int` | NO | PRI | FK → `crew.crew_id` |
| `role` | `varchar(20)` | NO |  |  |
| `assigned_at` | `timestamp` | NO |  | default `CURRENT_TIMESTAMP` |
| `unassigned_at` | `timestamp` | YES |  |  |

#### `crew_certification` (table, 533 rows)

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `crew_id` | `int` | NO | PRI | FK → `crew.crew_id` |
| `type_id` | `int` | NO | PRI | FK → `aircraft_type.type_id` |
| `certified_date` | `date` | NO |  |  |
| `expiry_date` | `date` | NO |  |  |
| `created_at` | `timestamp` | NO |  | default `CURRENT_TIMESTAMP` |

#### `delay_code` (table, 31 rows)

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `code_id` | `int` | NO | PRI | auto_increment |
| `iata_code` | `char(2)` | NO | UNI |  |
| `description` | `varchar(120)` | NO |  |  |
| `reason_id` | `int` | NO | MUL | FK → `delay_reason.reason_id` |

#### `delay_impact` (table, 40 rows)

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `impact_id` | `int` | NO | PRI | auto_increment |
| `delay_id` | `int` | NO | MUL | FK → `flight_delay.delay_id` |
| `flight_id` | `int` | NO | MUL | FK → `flight.flight_id` |
| `cause_flight_id` | `int` | YES | MUL | FK → `flight.flight_id` |
| `link` | `enum('AIRCRAFT','CREW','GATE','SLOT')` | NO |  |  |
| `minutes_added` | `int` | NO |  |  |
| `old_etd` | `datetime` | NO |  |  |
| `new_etd` | `datetime` | NO |  |  |
| `pass_no` | `int` | NO |  |  |

#### `delay_reason` (table, 8 rows)

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `reason_id` | `int` | NO | PRI | auto_increment |
| `category` | `enum('WEATHER','ATC','TECHNICAL','CREW','SECURITY','FUEL','MAINTENANCE','CASCADE')` | NO | MUL |  |
| `description` | `varchar(200)` | NO |  |  |
| `created_at` | `timestamp` | NO |  | default `CURRENT_TIMESTAMP` |

#### `duty_log` (table, 0 rows)

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `log_id` | `int` | NO | PRI | auto_increment |
| `crew_id` | `int` | NO | MUL | FK → `crew.crew_id` |
| `duty_date` | `date` | NO |  |  |
| `duty_start_time` | `datetime` | YES |  |  |
| `duty_end_time` | `datetime` | YES |  |  |
| `hours_flown` | `decimal(5,2)` | NO |  | default `0.00` |
| `hours_on_duty` | `decimal(5,2)` | NO |  | default `0.00` |

#### `flight` (table, 1,400 rows)

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `flight_id` | `int` | NO | PRI | auto_increment |
| `flight_number` | `varchar(10)` | NO |  |  |
| `route_id` | `int` | NO | MUL | FK → `route.route_id` |
| `aircraft_id` | `int` | NO | MUL | FK → `aircraft.aircraft_id` |
| `sched_departure` | `datetime` | NO | MUL |  |
| `sched_arrival` | `datetime` | NO |  |  |
| `boarding_start` | `datetime` | YES |  |  |
| `gate_close` | `datetime` | YES |  |  |
| `actual_departure` | `datetime` | YES |  |  |
| `actual_arrival` | `datetime` | YES |  |  |
| `status` | `enum('SCHEDULED','BOARDING','DEPARTED','ARRIVED','CANCELLED','DIVERTED')` | NO | MUL | default `SCHEDULED` |
| `delay_minutes` | `int` | NO |  | default `0` |
| `parent_flight_id` | `int` | YES | MUL | FK → `flight.flight_id` |
| `gate_id` | `int` | YES | MUL | FK → `gate.gate_id` |
| `remarks` | `varchar(200)` | YES |  |  |
| `created_at` | `timestamp` | NO |  | default `CURRENT_TIMESTAMP` |

#### `flight_delay` (table, 10 rows)

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `delay_id` | `int` | NO | PRI | auto_increment |
| `flight_id` | `int` | NO | MUL | FK → `flight.flight_id` |
| `code_id` | `int` | NO | MUL | FK → `delay_code.code_id` |
| `minutes` | `int` | NO |  |  |
| `sub_reason` | `varchar(200)` | YES |  |  |
| `phase` | `enum('PRE_BOARDING','AT_GATE','TAXI','AIRBORNE')` | NO |  | default `PRE_BOARDING` |
| `ops_status` | `enum('DELAYED','ON_HOLD','CANCELLED')` | NO |  | default `DELAYED` |
| `new_gate_id` | `int` | YES | MUL | FK → `gate.gate_id` |
| `new_boarding_time` | `datetime` | YES |  |  |
| `pax_deboarded` | `tinyint(1)` | NO |  | default `0` |
| `swap_aircraft_id` | `int` | YES | MUL | FK → `aircraft.aircraft_id` |
| `announcement` | `varchar(500)` | YES |  |  |
| `meal_voucher` | `tinyint(1)` | NO |  | default `0` |
| `compensation_eligible` | `tinyint(1)` | NO |  | default `0` |
| `rebooking_offered` | `tinyint(1)` | NO |  | default `0` |
| `reported_by` | `varchar(80)` | NO |  |  |
| `remarks` | `varchar(500)` | YES |  |  |
| `recorded_at` | `timestamp` | NO |  | default `CURRENT_TIMESTAMP` |
| `resolved_at` | `timestamp` | YES |  |  |

#### `gate` (table, 168 rows)

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `gate_id` | `int` | NO | PRI | auto_increment |
| `airport_id` | `int` | NO | MUL | FK → `airport.airport_id` |
| `gate_code` | `varchar(6)` | NO |  |  |
| `terminal` | `varchar(4)` | NO |  |  |

#### `maintenance_log` (table, 40 rows)

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `maint_id` | `int` | NO | PRI | auto_increment |
| `aircraft_id` | `int` | NO | MUL | FK → `aircraft.aircraft_id` |
| `maint_start` | `datetime` | NO |  |  |
| `maint_end` | `datetime` | NO |  |  |
| `type` | `enum('SCHEDULED','UNSCHEDULED','A_CHECK','B_CHECK','C_CHECK','D_CHECK','LINE_MAINTENANCE')` | NO |  |  |
| `downtime_hours` | `decimal(5,2)` | YES |  | VIRTUAL GENERATED |
| `created_at` | `timestamp` | NO |  | default `CURRENT_TIMESTAMP` |

#### `passenger` (table, 2,000 rows)

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `passenger_id` | `int` | NO | PRI | auto_increment |
| `name` | `varchar(80)` | NO |  |  |
| `passport_no` | `varchar(20)` | YES | UNI |  |
| `email` | `varchar(80)` | YES |  |  |
| `phone` | `varchar(20)` | YES |  |  |
| `date_of_birth` | `date` | NO |  |  |
| `created_at` | `timestamp` | NO |  | default `CURRENT_TIMESTAMP` |
| `updated_at` | `timestamp` | NO |  | on update CURRENT_TIMESTAMP; default `CURRENT_TIMESTAMP` |

#### `route` (table, 198 rows)

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `route_id` | `int` | NO | PRI | auto_increment |
| `origin_airport_id` | `int` | NO | MUL | FK → `airport.airport_id` |
| `dest_airport_id` | `int` | NO | MUL | FK → `airport.airport_id` |
| `distance_km` | `int` | NO |  |  |
| `std_duration_min` | `int` | NO |  |  |
| `created_at` | `timestamp` | NO |  | default `CURRENT_TIMESTAMP` |
| `deactivated_at` | `timestamp` | YES |  |  |

#### `ticket` (table, 15,000 rows)

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `ticket_id` | `int` | NO | PRI | auto_increment |
| `booking_id` | `int` | NO | MUL | FK → `booking.booking_id` |
| `flight_id` | `int` | NO | MUL | FK → `flight.flight_id` |
| `seat_no` | `varchar(4)` | NO |  |  |
| `fare` | `decimal(10,2)` | NO |  |  |
| `class` | `enum('ECONOMY','PREMIUM','BUSINESS','FIRST')` | NO |  |  |
| `issued_at` | `timestamp` | NO |  | default `CURRENT_TIMESTAMP` |
| `checked_in_at` | `timestamp` | YES |  |  |
| `boarded_at` | `timestamp` | YES |  |  |

#### `v_curfew_risk` (view)

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `flight_id` | `int` | NO |  | default `0` |
| `flight_number` | `varchar(10)` | NO |  | default `` |
| `side` | `varchar(9)` | NO |  | default `` |
| `airport` | `char(3)` | NO |  | default `` |
| `at_time` | `datetime` | YES |  |  |
| `open_time` | `time` | YES |  |  |
| `close_time` | `time` | YES |  |  |

#### `v_duty_breaches` (view)

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `crew_id` | `int` | NO |  |  |
| `name` | `varchar(80)` | NO |  |  |
| `role` | `enum('CAPTAIN','FIRST_OFFICER','CABIN_CREW','PURSER')` | NO |  |  |
| `duty_date` | `date` | YES |  |  |
| `duty_start` | `datetime` | YES |  |  |
| `duty_end` | `datetime` | YES |  |  |
| `duty_hours` | `decimal(23,2)` | YES |  |  |
| `legs` | `bigint` | NO |  | default `0` |

#### `v_flight_times` (view)

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `flight_id` | `int` | NO |  | default `0` |
| `flight_number` | `varchar(10)` | NO |  |  |
| `status` | `enum('SCHEDULED','BOARDING','DEPARTED','ARRIVED','CANCELLED','DIVERTED')` | NO |  | default `SCHEDULED` |
| `delay_minutes` | `int` | NO |  | default `0` |
| `parent_flight_id` | `int` | YES |  |  |
| `aircraft_id` | `int` | NO |  |  |
| `registration` | `varchar(10)` | NO |  |  |
| `gate_id` | `int` | YES |  |  |
| `gate_code` | `varchar(6)` | YES |  |  |
| `remarks` | `varchar(200)` | YES |  |  |
| `route_id` | `int` | NO |  |  |
| `origin_airport_id` | `int` | NO |  |  |
| `dest_airport_id` | `int` | NO |  |  |
| `origin` | `char(3)` | NO |  |  |
| `dest` | `char(3)` | NO |  |  |
| `std` | `datetime` | NO |  |  |
| `sta` | `datetime` | NO |  |  |
| `etd` | `datetime` | YES |  |  |
| `eta` | `datetime` | YES |  |  |
| `boarding_start` | `datetime` | YES |  |  |
| `actual_departure` | `datetime` | YES |  |  |
| `actual_arrival` | `datetime` | YES |  |  |
| `display_status` | `varchar(9)` | NO |  | default `` |

#### `v_missed_connections` (view)

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `booking_id` | `int` | NO |  | default `0` |
| `pnr` | `char(6)` | NO |  |  |
| `passenger_id` | `int` | NO |  | default `0` |
| `passenger_name` | `varchar(80)` | NO |  |  |
| `in_flight_id` | `int` | NO |  | default `0` |
| `in_flight` | `varchar(10)` | NO |  |  |
| `out_flight_id` | `int` | NO |  | default `0` |
| `out_flight` | `varchar(10)` | NO |  |  |
| `connect_airport` | `char(3)` | NO |  |  |
| `in_eta` | `datetime` | YES |  |  |
| `out_etd` | `datetime` | YES |  |  |
| `connect_min` | `bigint` | YES |  |  |
| `min_connect_min` | `int` | NO |  | default `60` |

## 8. Database programming

### 8.1 Triggers

| Trigger | Timing | Event | Table |
|---|---|---|---|
| trg_check_duty_limit | BEFORE | INSERT | crew_assignment |
| trg_no_double_seat | BEFORE | INSERT | ticket |
| trg_update_duty | AFTER | UPDATE | flight |

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

| Procedure | Type | Parameters |
|---|---|---|
| analyse_cascade | PROCEDURE | 1 |
| book_ticket | PROCEDURE | 6 |
| compute_cascade_candidates | PROCEDURE | 0 |
| find_replacement_crew | PROCEDURE | 1 |
| reset_all_delays | PROCEDURE | 0 |
| simulate_delay | PROCEDURE | 17 |

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

| Table | Rows |
|---|---|
| aircraft | 40 |
| aircraft_type | 4 |
| airport | 20 |
| booking | 13,500 |
| cascade_candidate | 0 |
| crew | 400 |
| crew_assignment | 5,600 |
| crew_certification | 533 |
| delay_code | 31 |
| delay_impact | 40 |
| delay_reason | 8 |
| duty_log | 0 |
| flight | 1,400 |
| flight_delay | 10 |
| gate | 168 |
| maintenance_log | 40 |
| passenger | 2,000 |
| route | 198 |
| ticket | 15,000 |

- Schedule window: Wed 23 Sep 2026 05:30 to Wed 30 Sep 2026 00:41.
- Flight status mix at generation time: SCHEDULED 1,238, ARRIVED 141, DEPARTED 17, BOARDING 4.
- Two-leg connecting bookings: 1,500.
- Flights whose crew also fly a different aircraft the same day (cross-aircraft crew links): 384.
- With the 10 sample delays applied: 46 flights late, 25 missed connections, 0 crew duty breaches, 0 curfew risks.

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

| Methods | URL | Endpoint |
|---|---|---|
| GET | `/` | `dashboard.index` |
| GET | `/admin/` | `admin.index` |
| GET | `/admin/<entity>/` | `admin.list_view` |
| POST | `/admin/<entity>/<int:row_id>/delete` | `admin.delete` |
| GET, POST | `/admin/<entity>/<int:row_id>/edit` | `admin.edit` |
| GET, POST | `/admin/<entity>/new` | `admin.new` |
| GET | `/airports/` | `airports.list_view` |
| GET | `/airports/<int:airport_id>/board` | `airports.board` |
| GET | `/bookings/` | `bookings.list_view` |
| GET | `/bookings/<int:booking_id>` | `bookings.detail` |
| POST | `/bookings/<int:booking_id>/cancel` | `bookings.cancel` |
| POST | `/bookings/<int:booking_id>/ticket` | `bookings.add_ticket` |
| GET, POST | `/bookings/new` | `bookings.new` |
| POST | `/bookings/ticket/<int:ticket_id>/checkin` | `bookings.checkin` |
| GET | `/cascade/` | `cascade.index` |
| GET | `/cascade/<int:flight_id>` | `cascade.trace` |
| GET | `/crew/` | `crew.list_view` |
| GET | `/crew/<int:crew_id>` | `crew.detail` |
| POST | `/crew/<int:crew_id>/certify` | `crew.certify` |
| POST | `/crew/<int:crew_id>/certify/<int:type_id>/delete` | `crew.decertify` |
| POST | `/crew/<int:crew_id>/delete` | `crew.delete` |
| GET, POST | `/crew/<int:crew_id>/edit` | `crew.edit` |
| GET | `/crew/duty` | `crew.duty` |
| GET, POST | `/crew/new` | `crew.new` |
| GET | `/crew/replacement/<int:flight_id>` | `crew.replacement` |
| GET | `/delays/` | `delays.list_view` |
| GET | `/delays/<int:delay_id>` | `delays.detail` |
| GET, POST | `/delays/<int:delay_id>/edit` | `delays.edit` |
| POST | `/delays/<int:delay_id>/resolve` | `delays.resolve` |
| GET, POST | `/delays/reset` | `delays.reset` |
| GET | `/flights/` | `flights.list_view` |
| GET | `/flights/<int:flight_id>` | `flights.detail` |
| POST | `/flights/<int:flight_id>/assign-crew` | `flights.assign_crew` |
| GET, POST | `/flights/<int:flight_id>/delay` | `flights.delay` |
| POST | `/flights/<int:flight_id>/delete` | `flights.delete` |
| GET, POST | `/flights/<int:flight_id>/edit` | `flights.edit` |
| POST | `/flights/<int:flight_id>/unassign-crew/<int:crew_id>` | `flights.unassign_crew` |
| GET, POST | `/flights/new` | `flights.new` |
| GET | `/passengers/` | `passengers.list_view` |
| GET | `/passengers/<int:passenger_id>` | `passengers.detail` |
| POST | `/passengers/<int:passenger_id>/delete` | `passengers.delete` |
| GET, POST | `/passengers/<int:passenger_id>/edit` | `passengers.edit` |
| GET, POST | `/passengers/new` | `passengers.new` |
| GET | `/reports/` | `reports.index` |
| GET | `/reports/delay-causes` | `reports.delay_causes` |
| GET | `/reports/duty-status` | `reports.duty_status` |
| GET | `/reports/load-factor` | `reports.load_factor` |
| GET | `/reports/ontime` | `reports.ontime` |
| GET | `/reports/utilisation` | `reports.utilisation` |
| GET | `/schema/` | `schema.index` |
| GET | `/schema/<table_name>` | `schema.table_detail` |
| GET | `/schema/<table_name>/rows` | `schema.rows` |

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

- **Route smoke test:** 108/108 pages returned successfully.
- **`tests/test_cascade.py`: PASS**, output: `ok (12 knock-on flights)`
- **`tests/test_crew_assignment.py`: PASS**, output: `ok`
- **`tests/test_live_changes.py`: PASS**

```
PASS inserted passenger appears in search
PASS schema row count is exact after INSERT
PASS hand-set delay shows as DELAYED with new time
PASS airport rule change shows on its board
PASS new passenger column shows on the passenger page
PASS new airport column shows in admin list
PASS new airport column is editable
PASS value saved into the new column
PASS new ENUM value offered in the flight form
PASS flight in the new status displays it
PASS new crew role offered in the crew form
PASS SQL-inserted airport appears on Airports
PASS SQL-inserted airport appears on the dashboard map data
PASS new view listed on Schema
PASS new view's rows browsable
PASS deleted passenger is gone
PASS renamed column shows under its new name
PASS breaking change gives a readable error page
18/18 checks passed; database rebuilt.
```

### 15.3 A worked cascade (measured just now on a fresh database)

**Scenario:** starting from a network with no delays, file a 180-minute delay on **AI-101 (DEL → HYD, aircraft VT-A01, STD Thu 24 Sep 05:40)** with IATA code 41 (aircraft defect), "Hydraulic leak found on walk-around", phase At gate.

**Result:** the engine ran in **1.23 s** over all 1,400 flights and made **12 knock-on changes** in 6 passes (AIRCRAFT 9, CREW 2, SLOT 1), totalling 835 knock-on minutes. AI-101's ETD moved to Thu 08:40. It reached 2 aircraft and 5 airports, affected 87 passengers and broke 7 connections (0 duty breaches, 0 curfew risks).

Every knock-on change, as logged in `delay_impact`:

| Pass | Flight | Route | Aircraft | Link | Caused by | ETD before | ETD after | Added |
|---|---|---|---|---|---|---|---|---|
| 1 | AI-102 | HYD→DEL | VT-A01 | AIRCRAFT | AI-101 | Thu 08:28 | Thu 11:13 | +165 |
| 2 | AI-102 | HYD→DEL | VT-A01 | SLOT | HYD runway slot | Thu 11:13 | Thu 12:00 | +47 |
| 2 | AI-109 | DEL→CCU | VT-A02 | CREW | AI-102 | Thu 13:22 | Thu 13:41 | +19 |
| 2 | AI-103 | DEL→GAU | VT-A01 | AIRCRAFT | AI-102 | Thu 11:11 | Thu 13:56 | +165 |
| 3 | AI-109 | DEL→CCU | VT-A02 | CREW | AI-102 | Thu 13:41 | Thu 14:28 | +47 |
| 3 | AI-103 | DEL→GAU | VT-A01 | AIRCRAFT | AI-102 | Thu 13:56 | Thu 14:43 | +47 |
| 3 | AI-104 | GAU→DEL | VT-A01 | AIRCRAFT | AI-103 | Thu 13:19 | Thu 15:59 | +160 |
| 3 | AI-110 | CCU→DEL | VT-A02 | AIRCRAFT | AI-109 | Thu 16:01 | Thu 16:10 | +9 |
| 4 | AI-104 | GAU→DEL | VT-A01 | AIRCRAFT | AI-103 | Thu 15:59 | Thu 16:46 | +47 |
| 4 | AI-110 | CCU→DEL | VT-A02 | AIRCRAFT | AI-109 | Thu 16:10 | Thu 16:57 | +47 |
| 5 | AI-111 | DEL→BOM | VT-A02 | AIRCRAFT | AI-110 | Thu 18:55 | Thu 19:36 | +41 |
| 6 | AI-112 | BOM→DEL | VT-A02 | AIRCRAFT | AI-111 | Thu 21:21 | Thu 22:02 | +41 |

Passengers who now miss connections (from `v_missed_connections`; a negative connection means the onward flight now leaves before the inbound lands):

| PNR | Passenger | Inbound | Onward | At | Connection | Needs |
|---|---|---|---|---|---|---|
| PN09FH | Ananya Joshi | AI-101 | AI-307 | HYD | 13 min | 60 min |
| PN09L1 | Ananya Joshi | AI-101 | AI-163 | HYD | 39 min | 60 min |
| PN09B6 | Sai Bhatt | AI-102 | AI-253 | DEL | -45 min | 75 min |
| PN09KQ | Sai Kulkarni | AI-102 | AI-109 | DEL | 45 min | 75 min |
| PN0A43 | Sneha Iyer | AI-102 | AI-140 | DEL | 40 min | 75 min |
| PN0A2M | Rohan Rao | AI-103 | AI-332 | GAU | -155 min | 45 min |
| PN09SW | Nikhil Khan | AI-110 | AI-183 | DEL | 23 min | 75 min |

How to read it: AIRCRAFT rows follow the same aircraft's day; a CREW row is where crew arriving late are rostered onto a different aircraft, so the delay jumps aircraft; SLOT rows are flights pushed into the next hour because the airport's departures for that hour were full.

### 15.4 Sample delays in the seeded database

| # | Flight | Route | IATA | Category | Details | Minutes | Other flights moved | Knock-on minutes |
|---|---|---|---|---|---|---|---|---|
| 1 | AI-113 | BOM→HYD | 71 | WEATHER | Dense fog at DEL, RVR below CAT I minima | 95 | 3 | 225 |
| 2 | AI-145 | MAA→IXC | 81 | ATC | Flow restriction over Nagpur FIR | 40 | 3 | 70 |
| 3 | AI-161 | HYD→COK | 41 | TECHNICAL | Hydraulic system B low pressure on pre-flight check | 150 | 7 | 868 |
| 4 | AI-180 | JAI→DEL | 63 | CREW | Late crew reporting after rest-period dispute | 30 | 3 | 40 |
| 5 | AI-209 | MAA→IXC | 85 | SECURITY | Unattended bag in security hold area | 60 | 3 | 160 |
| 6 | AI-229 | CCU→GOI | 36 | FUEL | Fuel bowser breakdown at stand | 75 | 3 | 175 |
| 7 | AI-257 | BOM→NAG | 43 | MAINTENANCE | Bird strike inspection after previous sector | 200 | 7 | 630 |
| 8 | AI-279 | BLR→JAI | 93 | CASCADE | Inbound aircraft late from previous rotation | 45 | 1 | 45 |
| 9 | AI-305 | HYD→BOM | 72 | WEATHER | Thunderstorms at destination, holding expected | 120 | 7 | 340 |
| 10 | AI-325 | DEL→BBI | 89 | ATC | Runway 27 closed for friction testing | 35 | 3 | 55 |

**Totals:** 850 minutes filed directly caused **2,608 knock-on minutes** across 40 other flight changes, a reactionary-to-primary ratio of about **3.1 : 1**. Knock-on changes by link: AIRCRAFT 37, CREW 2, SLOT 1.

### 15.5 Report query outputs (seeded database)

**q3 on-time performance** (`database/queries/q3_ontime_performance.sql`)

```
+-------------+---------------+-----------------+-------------+
| flight_date | total_flights | on_time_flights | on_time_pct |
+-------------+---------------+-----------------+-------------+
| 2026-09-23  |           200 |             200 |       100.0 |
| 2026-09-24  |           200 |             200 |       100.0 |
| 2026-09-25  |           200 |             193 |        96.5 |
| 2026-09-26  |           200 |             191 |        95.5 |
| 2026-09-27  |           200 |             192 |        96.0 |
| 2026-09-28  |           200 |             191 |        95.5 |
| 2026-09-29  |           200 |             193 |        96.5 |
+-------------+---------------+-----------------+-------------+
```

**q4 delay causes** (`database/queries/q4_top_delay_causes.sql`)

```
+-------------+-------------+---------------+-------------+
| category    | delay_count | total_minutes | avg_minutes |
+-------------+-------------+---------------+-------------+
| WEATHER     |           2 |           215 |       107.5 |
| ATC         |           2 |            75 |        37.5 |
| TECHNICAL   |           1 |           150 |       150.0 |
| CREW        |           1 |            30 |        30.0 |
| SECURITY    |           1 |            60 |        60.0 |
| FUEL        |           1 |            75 |        75.0 |
| MAINTENANCE |           1 |           200 |       200.0 |
| CASCADE     |           1 |            45 |        45.0 |
+-------------+-------------+---------------+-------------+
```

**q6 load factor (first rows)** (`database/queries/q6_load_factor.sql`)

```
+-----------+---------------+---------------------+---------------+--------------+-----------------+
| flight_id | flight_number | sched_departure     | seat_capacity | tickets_sold | load_factor_pct |
+-----------+---------------+---------------------+---------------+--------------+-----------------+
|         1 | AI-137        | 2026-09-23 05:30:00 |           180 |           11 |             6.1 |
|         2 | AI-185        | 2026-09-23 05:30:00 |           189 |           10 |             5.3 |
|         3 | AI-233        | 2026-09-23 05:30:00 |           220 |           11 |             5.0 |
|         4 | AI-281        | 2026-09-23 05:30:00 |           180 |           11 |             6.1 |
|         5 | AI-329        | 2026-09-23 05:30:00 |           189 |           10 |             5.3 |
|         6 | AI-101        | 2026-09-23 05:40:00 |           180 |           10 |             5.6 |
|         7 | AI-149        | 2026-09-23 05:40:00 |           189 |            8 |             4.2 |
|         8 | AI-197        | 2026-09-23 05:40:00 |           220 |           10 |             4.5 |
|         9 | AI-245        | 2026-09-23 05:40:00 |           180 |           10 |             5.6 |
... (1391 more rows)
+-----------+---------------+---------------------+---------------+--------------+-----------------+
```

**q7 crew duty status** (`database/queries/q7_duty_status.sql`)

```
(empty result)
```

**q8 aircraft utilisation (first rows)** (`database/queries/q8_aircraft_utilisation.sql`)

```
+-------------+--------------+------------+------------------+------------------------+-------------------+
| aircraft_id | registration | model      | flights_operated | scheduled_flight_hours | total_delay_hours |
+-------------+--------------+------------+------------------+------------------------+-------------------+
|          40 | VT-A40       | B777-300ER |               42 |                   74.7 |               0.0 |
|           4 | VT-A04       | A320-200   |               42 |                   76.9 |               0.0 |
|          30 | VT-A30       | B777-300ER |               42 |                   74.5 |               1.5 |
|          20 | VT-A20       | B777-300ER |               42 |                   76.8 |               0.0 |
|          16 | VT-A16       | A320-200   |               42 |                   72.8 |               0.0 |
|          10 | VT-A10       | B777-300ER |               42 |                   77.6 |               0.0 |
|          22 | VT-A22       | A320-200   |               42 |                   77.8 |               4.2 |
|          36 | VT-A36       | B737-800   |               42 |                   77.6 |               0.0 |
|          28 | VT-A28       | A320-200   |               42 |                   75.6 |               1.3 |
... (31 more rows)
+-------------+--------------+------------+------------------+------------------------+-------------------+
```

## 16. Development history, challenges, limitations and future work

### 16.1 How the project was built (iterations)

| Commit | Date | Message |
|---|---|---|
| a615e80 | 23 Sep 2026 10:13 | Organisation-wide delay cascade: delay notices, gates, slots, crew links, airport boards |
| 05bcf83 | 23 Sep 2026 09:37 | Add design spec for organisation-wide delay cascade |
| efa402c | 07 Sep 2026 19:37 | Build the Flask app layer: 9 blueprints, services, templates, docs |
| 3b93f8d | 07 Sep 2026 15:09 | Initial commit: airline-cascades project |

(Work after the last commit is in the working tree when this file was generated.)

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

| File | Lines |
|---|---|
| `.env.example` | 5 |
| `.gitignore` | 7 |
| `app.py` | 97 |
| `database/00_drop_all.sql` | 22 |
| `database/01_schema.sql` | 295 |
| `database/02_seed_reference.sql` | 89 |
| `database/03_seed_operational.sql` | 341 |
| `database/04_triggers.sql` | 74 |
| `database/05_procedures.sql` | 284 |
| `database/06_views.sql` | 78 |
| `database/07_seed_delays.sql` | 24 |
| `database/queries/q1_cascade_trace.sql` | 14 |
| `database/queries/q2_replacement_crew.sql` | 26 |
| `database/queries/q3_ontime_performance.sql` | 10 |
| `database/queries/q4_top_delay_causes.sql` | 11 |
| `database/queries/q5_cascade_passengers.sql` | 14 |
| `database/queries/q6_load_factor.sql` | 17 |
| `database/queries/q7_duty_status.sql` | 10 |
| `database/queries/q8_aircraft_utilisation.sql` | 11 |
| `database/setup.sql` | 8 |
| `requirements.txt` | 3 |
| `scripts/build_report_context.py` | 355 |
| `scripts/reset_db.sh` | 4 |
| `scripts/run.sh` | 5 |
| `scripts/setup_db.sh` | 31 |
| `src/__init__.py` | 0 |
| `src/config.py` | 14 |
| `src/db.py` | 76 |
| `src/routes/__init__.py` | 0 |
| `src/routes/admin.py` | 73 |
| `src/routes/airports.py` | 29 |
| `src/routes/bookings.py` | 83 |
| `src/routes/cascade.py` | 25 |
| `src/routes/crew.py` | 91 |
| `src/routes/dashboard.py` | 31 |
| `src/routes/delays.py` | 131 |
| `src/routes/flights.py` | 121 |
| `src/routes/helpers.py` | 16 |
| `src/routes/passengers.py` | 78 |
| `src/routes/reports.py` | 35 |
| `src/routes/schema.py` | 36 |
| `src/services/__init__.py` | 0 |
| `src/services/admin.py` | 250 |
| `src/services/airports.py` | 35 |
| `src/services/bookings.py` | 66 |
| `src/services/cascade.py` | 24 |
| `src/services/crew.py` | 88 |
| `src/services/dashboard.py` | 48 |
| `src/services/delays.py` | 136 |
| `src/services/flights.py` | 165 |
| `src/services/lookups.py` | 77 |
| `src/services/passengers.py` | 57 |
| `src/services/reports.py` | 52 |
| `src/services/schema_info.py` | 69 |
| `static/css/style.css` | 536 |
| `static/js/ambient.js` | 47 |
| `static/js/constellation.js` | 320 |
| `templates/_macros.html` | 48 |
| `templates/_status.html` | 8 |
| `templates/admin/form.html` | 26 |
| `templates/admin/index.html` | 11 |
| `templates/admin/list.html` | 33 |
| `templates/airports/board.html` | 63 |
| `templates/airports/list.html` | 31 |
| `templates/base.html` | 67 |
| `templates/bookings/detail.html` | 65 |
| `templates/bookings/form.html` | 29 |
| `templates/bookings/list.html` | 32 |
| `templates/cascade/index.html` | 23 |
| `templates/cascade/trace.html` | 37 |
| `templates/crew/detail.html` | 56 |
| `templates/crew/duty.html` | 21 |
| `templates/crew/form.html` | 16 |
| `templates/crew/list.html` | 34 |
| `templates/crew/replacement.html` | 17 |
| `templates/dashboard/index.html` | 71 |
| `templates/delays/detail.html` | 128 |
| `templates/delays/edit.html` | 19 |
| `templates/delays/form.html` | 158 |
| `templates/delays/list.html` | 31 |
| `templates/delays/reset.html` | 11 |
| `templates/error.html` | 19 |
| `templates/flights/detail.html` | 108 |
| `templates/flights/form.html` | 23 |
| `templates/flights/list.html` | 45 |
| `templates/passengers/detail.html` | 38 |
| `templates/passengers/form.html` | 14 |
| `templates/passengers/list.html` | 27 |
| `templates/reports/delay_causes.html` | 15 |
| `templates/reports/duty_status.html` | 15 |
| `templates/reports/index.html` | 13 |
| `templates/reports/load_factor.html` | 15 |
| `templates/reports/ontime.html` | 15 |
| `templates/reports/utilisation.html` | 15 |
| `templates/schema/index.html` | 32 |
| `templates/schema/rows.html` | 33 |
| `templates/schema/table.html` | 37 |
| `tests/test_cascade.py` | 79 |
| `tests/test_crew_assignment.py` | 38 |
| `tests/test_live_changes.py` | 100 |

**Total: 6,360 lines** (excluding documentation).

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

| File | Shows |
|---|---|
| `docs/screenshots/01-dashboard.png` | Dashboard: live headline, date, summary and the network constellation map |
| `docs/screenshots/02-dashboard-map-hover.png` | Map interaction: hovering Delhi draws its 19 routes and shows its tooltip |
| `docs/screenshots/03-dashboard-full.png` | Full dashboard: figures, airport-board shortcuts, recent delays |
| `docs/screenshots/04-flights-delayed.png` | Flights filtered to Delayed: scheduled times struck through, estimates in amber |
| `docs/screenshots/05-flight-detail.png` | Flight detail: times, crew assignment, delays filed, knock-on received, all columns |
| `docs/screenshots/06-delay-form.png` | Delay form filled in: IATA code, 180 minutes, auto-filled ETD/ETA/boarding, announcement, vouchers |
| `docs/screenshots/07-delay-log.png` | Delay log: every notice with its knock-on count and minutes |
| `docs/screenshots/08-airports.png` | Airports: operating rules, gates, departures today, late departures |
| `docs/screenshots/09-airport-board.png` | Delhi departure and arrival board with the day picker (carousel dots) |
| `docs/screenshots/10-crew-profile.png` | Crew profile (Team Member Card): role, name, certifications |
| `docs/screenshots/11-passengers.png` | Passengers list with the Section Headline Block |
| `docs/screenshots/12-booking-connection.png` | A two-leg connecting booking with its tickets |
| `docs/screenshots/13-reports.png` | Reports index |
| `docs/screenshots/14-report-ontime.png` | On-time performance report |
| `docs/screenshots/15-admin-airports.png` | Admin: airports with their timing rules (generic CRUD) |
| `docs/screenshots/16-admin-airport-edit.png` | Admin: editing an airport's curfew, slots, connection and turnaround times |
| `docs/screenshots/17-schema.png` | Schema browser: tables with exact row counts, and views |
| `docs/screenshots/18-schema-rows.png` | Live row browser for a table (flight_delay) |
| `docs/screenshots/19-delay-impact.png` | Impact page after filing the 180-min delay: figures, notice, every knock-on change, missed connections |
| `docs/screenshots/20-cascade-trace.png` | Cascade trace: recursive tree of the delayed flight and passengers affected |
| `docs/screenshots/21-board-after-delay.png` | Delhi board after the delay: changed times highlighted |
| `docs/screenshots/22-mobile-dashboard.png` | Dashboard at phone width (390px) |
| `docs/screenshots/23-mobile-flights.png` | Flights at phone width: horizontally scrolling table |

---

# Appendices: complete source code

Everything below is the project's source as it was when this file was
generated. `.env` (credentials) is deliberately excluded. Other docs in the
repository are included at the end.

### A.1 `database/00_drop_all.sql`

````sql
SET FOREIGN_KEY_CHECKS = 0;
DROP VIEW IF EXISTS v_missed_connections, v_duty_breaches, v_curfew_risk, v_flight_times;
DROP TABLE IF EXISTS cascade_candidate;
DROP TABLE IF EXISTS delay_impact;
DROP TABLE IF EXISTS ticket;
DROP TABLE IF EXISTS flight_delay;
DROP TABLE IF EXISTS crew_assignment;
DROP TABLE IF EXISTS booking;
DROP TABLE IF EXISTS maintenance_log;
DROP TABLE IF EXISTS duty_log;
DROP TABLE IF EXISTS crew_certification;
DROP TABLE IF EXISTS flight;
DROP TABLE IF EXISTS passenger;
DROP TABLE IF EXISTS crew;
DROP TABLE IF EXISTS aircraft;
DROP TABLE IF EXISTS route;
DROP TABLE IF EXISTS delay_code;
DROP TABLE IF EXISTS gate;
DROP TABLE IF EXISTS delay_reason;
DROP TABLE IF EXISTS aircraft_type;
DROP TABLE IF EXISTS airport;
SET FOREIGN_KEY_CHECKS = 1;
````

### A.2 `database/01_schema.sql`

````sql
SET FOREIGN_KEY_CHECKS = 0;

-- ============= LAYER 1 =============

CREATE TABLE airport (
  airport_id  INT AUTO_INCREMENT PRIMARY KEY,
  iata_code   CHAR(3) NOT NULL UNIQUE,
  icao_code   CHAR(4) UNIQUE,
  city        VARCHAR(60) NOT NULL,
  country     VARCHAR(60) NOT NULL,
  timezone    VARCHAR(40) NOT NULL,
  -- Airport operating rules used by the cascade engine (simulate_delay).
  open_time              TIME NULL,              -- curfew window; NULL/NULL = open 24h
  close_time             TIME NULL,
  runway_slots_per_hour  INT DEFAULT 6 NOT NULL,  -- max departures per clock hour
  min_connect_min        INT DEFAULT 60 NOT NULL, -- minimum passenger connection time
  min_turnaround_min     INT DEFAULT 45 NOT NULL, -- minimum aircraft ground time
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  CONSTRAINT chk_airport_slots CHECK (runway_slots_per_hour > 0),
  CONSTRAINT chk_airport_mct CHECK (min_connect_min > 0),
  CONSTRAINT chk_airport_tat CHECK (min_turnaround_min > 0),
  CONSTRAINT chk_airport_curfew CHECK ((open_time IS NULL AND close_time IS NULL) OR open_time < close_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE aircraft_type (
  type_id           INT AUTO_INCREMENT PRIMARY KEY,
  model             VARCHAR(40) NOT NULL,
  manufacturer      VARCHAR(40) NOT NULL,
  seat_capacity     INT NOT NULL CHECK (seat_capacity > 0),
  max_range_km      INT NOT NULL CHECK (max_range_km > 0),
  cruise_speed_kmh  INT CHECK (cruise_speed_kmh > 0),
  created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  UNIQUE KEY uq_type (model, manufacturer)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE delay_reason (
  reason_id   INT AUTO_INCREMENT PRIMARY KEY,
  category    ENUM('WEATHER','ATC','TECHNICAL','CREW',
                   'SECURITY','FUEL','MAINTENANCE','CASCADE') NOT NULL,
  description VARCHAR(200) NOT NULL,
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  UNIQUE KEY uq_reason (category, description)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============= LAYER 2 =============

CREATE TABLE gate (
  gate_id     INT AUTO_INCREMENT PRIMARY KEY,
  airport_id  INT NOT NULL,
  gate_code   VARCHAR(6) NOT NULL,
  terminal    VARCHAR(4) NOT NULL,
  UNIQUE KEY uq_gate (airport_id, gate_code),
  FOREIGN KEY (airport_id) REFERENCES airport(airport_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- IATA standard delay codes (AHM 730), each mapped to one of our 8 categories.
CREATE TABLE delay_code (
  code_id      INT AUTO_INCREMENT PRIMARY KEY,
  iata_code    CHAR(2) NOT NULL UNIQUE,
  description  VARCHAR(120) NOT NULL,
  reason_id    INT NOT NULL,
  FOREIGN KEY (reason_id) REFERENCES delay_reason(reason_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE route (
  route_id           INT AUTO_INCREMENT PRIMARY KEY,
  origin_airport_id  INT NOT NULL,
  dest_airport_id    INT NOT NULL,
  distance_km        INT NOT NULL CHECK (distance_km > 0),
  std_duration_min   INT NOT NULL CHECK (std_duration_min > 0),
  created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  deactivated_at     TIMESTAMP NULL,
  CONSTRAINT chk_route_distinct CHECK (origin_airport_id <> dest_airport_id),
  UNIQUE KEY uq_route (origin_airport_id, dest_airport_id),
  FOREIGN KEY (origin_airport_id) REFERENCES airport(airport_id) ON DELETE RESTRICT,
  FOREIGN KEY (dest_airport_id)   REFERENCES airport(airport_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE aircraft (
  aircraft_id      INT AUTO_INCREMENT PRIMARY KEY,
  registration     VARCHAR(10) NOT NULL UNIQUE,
  type_id          INT NOT NULL,
  base_airport_id  INT NOT NULL,
  status           ENUM('ACTIVE','MAINTENANCE','GROUNDED','RETIRED')
                     DEFAULT 'ACTIVE' NOT NULL,
  created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  retired_at       TIMESTAMP NULL,
  FOREIGN KEY (type_id)         REFERENCES aircraft_type(type_id) ON DELETE RESTRICT,
  FOREIGN KEY (base_airport_id) REFERENCES airport(airport_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE crew (
  crew_id          INT AUTO_INCREMENT PRIMARY KEY,
  name             VARCHAR(80) NOT NULL,
  role             ENUM('CAPTAIN','FIRST_OFFICER','CABIN_CREW','PURSER') NOT NULL,
  base_airport_id  INT NOT NULL,
  hire_date        DATE NOT NULL,
  terminated_at    TIMESTAMP NULL,
  created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  FOREIGN KEY (base_airport_id) REFERENCES airport(airport_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE passenger (
  passenger_id  INT AUTO_INCREMENT PRIMARY KEY,
  name          VARCHAR(80) NOT NULL,
  passport_no   VARCHAR(20) UNIQUE,
  email         VARCHAR(80),
  phone         VARCHAR(20),
  date_of_birth DATE NOT NULL,
  -- age is NOT a generated column: MySQL 8 disallows non-deterministic functions
  -- (CURDATE/NOW) in generated column expressions (error 3763). Computed at query
  -- time instead via TIMESTAMPDIFF(YEAR, date_of_birth, CURDATE()) -- see DEVIATIONS.md.
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL
  -- "date_of_birth must be in the past" is NOT a CHECK constraint: MySQL 8 disallows
  -- non-deterministic functions (CURDATE/NOW) in CHECK expressions (error 3814).
  -- Enforced in the Flask form instead -- see DEVIATIONS.md.
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============= LAYER 3 =============

CREATE TABLE flight (
  flight_id         INT AUTO_INCREMENT PRIMARY KEY,
  flight_number     VARCHAR(10) NOT NULL,
  route_id          INT NOT NULL,
  aircraft_id       INT NOT NULL,
  sched_departure   DATETIME NOT NULL,
  sched_arrival     DATETIME NOT NULL,
  boarding_start    DATETIME NULL,
  gate_close        DATETIME NULL,
  actual_departure  DATETIME NULL,
  actual_arrival    DATETIME NULL,
  status            ENUM('SCHEDULED','BOARDING','DEPARTED',
                         'ARRIVED','CANCELLED','DIVERTED')
                      DEFAULT 'SCHEDULED' NOT NULL,
  delay_minutes     INT DEFAULT 0 NOT NULL,  -- DENORMALIZED: maintained by simulate_delay()
  parent_flight_id  INT NULL,
  gate_id           INT NULL,                -- departure gate
  remarks           VARCHAR(200) NULL,
  created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  CONSTRAINT chk_flight_times CHECK (sched_arrival > sched_departure),
  -- chk_no_self_parent dropped: MySQL 8 disallows a column used in a CHECK constraint
  -- when it also has a FK referential action (parent_flight_id has ON DELETE SET NULL,
  -- error 3823). The cascade trigger never sets parent_flight_id = flight_id, so the
  -- invariant holds regardless -- see DEVIATIONS.md.
  FOREIGN KEY (route_id)         REFERENCES route(route_id) ON DELETE RESTRICT,
  FOREIGN KEY (aircraft_id)      REFERENCES aircraft(aircraft_id) ON DELETE RESTRICT,
  FOREIGN KEY (parent_flight_id) REFERENCES flight(flight_id) ON DELETE SET NULL,
  FOREIGN KEY (gate_id)          REFERENCES gate(gate_id) ON DELETE SET NULL,
  INDEX idx_flight_aircraft (aircraft_id),
  INDEX idx_flight_sched (sched_departure),
  INDEX idx_flight_parent (parent_flight_id),
  INDEX idx_flight_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE crew_certification (
  crew_id         INT NOT NULL,
  type_id         INT NOT NULL,
  certified_date  DATE NOT NULL,
  expiry_date     DATE NOT NULL,
  created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  PRIMARY KEY (crew_id, type_id),
  CONSTRAINT chk_cert_expiry CHECK (expiry_date > certified_date),
  FOREIGN KEY (crew_id) REFERENCES crew(crew_id) ON DELETE CASCADE,
  FOREIGN KEY (type_id) REFERENCES aircraft_type(type_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE duty_log (
  log_id           INT AUTO_INCREMENT PRIMARY KEY,
  crew_id          INT NOT NULL,
  duty_date        DATE NOT NULL,
  duty_start_time  DATETIME NULL,
  duty_end_time    DATETIME NULL,
  hours_flown      DECIMAL(5,2) DEFAULT 0 NOT NULL,   -- DENORMALIZED
  hours_on_duty    DECIMAL(5,2) DEFAULT 0 NOT NULL,   -- DENORMALIZED
  UNIQUE KEY uq_duty_crew_date (crew_id, duty_date),
  CONSTRAINT chk_duty_hours CHECK (hours_flown >= 0 AND hours_on_duty >= 0),
  FOREIGN KEY (crew_id) REFERENCES crew(crew_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE maintenance_log (
  maint_id        INT AUTO_INCREMENT PRIMARY KEY,
  aircraft_id     INT NOT NULL,
  maint_start     DATETIME NOT NULL,
  maint_end       DATETIME NOT NULL,
  type            ENUM('SCHEDULED','UNSCHEDULED','A_CHECK','B_CHECK',
                       'C_CHECK','D_CHECK','LINE_MAINTENANCE') NOT NULL,
  downtime_hours  DECIMAL(5,2) GENERATED ALWAYS AS
    (TIMESTAMPDIFF(MINUTE, maint_start, maint_end) / 60) VIRTUAL,
  created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  CONSTRAINT chk_maint_times CHECK (maint_end > maint_start),
  FOREIGN KEY (aircraft_id) REFERENCES aircraft(aircraft_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE booking (
  booking_id    INT AUTO_INCREMENT PRIMARY KEY,
  pnr           CHAR(6) NOT NULL UNIQUE,
  passenger_id  INT NOT NULL,
  booking_date  DATE DEFAULT (CURRENT_DATE) NOT NULL,
  status        ENUM('CONFIRMED','CANCELLED','CHECKED_IN','COMPLETED')
                  DEFAULT 'CONFIRMED' NOT NULL,
  cancelled_at  TIMESTAMP NULL,
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
  FOREIGN KEY (passenger_id) REFERENCES passenger(passenger_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============= LAYER 4 =============

CREATE TABLE crew_assignment (
  flight_id      INT NOT NULL,
  crew_id        INT NOT NULL,
  role           VARCHAR(20) NOT NULL,
  assigned_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  unassigned_at  TIMESTAMP NULL,
  PRIMARY KEY (flight_id, crew_id),
  FOREIGN KEY (flight_id) REFERENCES flight(flight_id) ON DELETE CASCADE,
  FOREIGN KEY (crew_id)   REFERENCES crew(crew_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- A delay notice as filed by the duty manager. The category (delay_reason) is
-- reached through the IATA code, not stored here: code -> reason is a
-- dependency of delay_code, so a copy on this table would break 3NF.
CREATE TABLE flight_delay (
  delay_id               INT AUTO_INCREMENT PRIMARY KEY,
  flight_id              INT NOT NULL,
  code_id                INT NOT NULL,
  minutes                INT NOT NULL CHECK (minutes >= 0),
  sub_reason             VARCHAR(200) NULL,
  phase                  ENUM('PRE_BOARDING','AT_GATE','TAXI','AIRBORNE')
                           DEFAULT 'PRE_BOARDING' NOT NULL,
  ops_status             ENUM('DELAYED','ON_HOLD','CANCELLED') DEFAULT 'DELAYED' NOT NULL,
  new_gate_id            INT NULL,
  new_boarding_time      DATETIME NULL,
  pax_deboarded          BOOLEAN DEFAULT FALSE NOT NULL,
  swap_aircraft_id       INT NULL,
  announcement           VARCHAR(500) NULL,
  meal_voucher           BOOLEAN DEFAULT FALSE NOT NULL,
  compensation_eligible  BOOLEAN DEFAULT FALSE NOT NULL,
  rebooking_offered      BOOLEAN DEFAULT FALSE NOT NULL,
  reported_by            VARCHAR(80) NOT NULL,
  remarks                VARCHAR(500) NULL,
  recorded_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  resolved_at            TIMESTAMP NULL,
  CONSTRAINT chk_delay_resolve CHECK (resolved_at IS NULL OR resolved_at >= recorded_at),
  FOREIGN KEY (flight_id)        REFERENCES flight(flight_id) ON DELETE CASCADE,
  FOREIGN KEY (code_id)          REFERENCES delay_code(code_id) ON DELETE RESTRICT,
  FOREIGN KEY (new_gate_id)      REFERENCES gate(gate_id) ON DELETE SET NULL,
  FOREIGN KEY (swap_aircraft_id) REFERENCES aircraft(aircraft_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- One row per knock-on change the cascade engine made while processing a notice.
CREATE TABLE delay_impact (
  impact_id        INT AUTO_INCREMENT PRIMARY KEY,
  delay_id         INT NOT NULL,
  flight_id        INT NOT NULL,
  cause_flight_id  INT NULL,               -- NULL for SLOT (airport congestion)
  link             ENUM('AIRCRAFT','CREW','GATE','SLOT') NOT NULL,
  minutes_added    INT NOT NULL CHECK (minutes_added > 0),
  old_etd          DATETIME NOT NULL,
  new_etd          DATETIME NOT NULL,
  pass_no          INT NOT NULL,
  FOREIGN KEY (delay_id)        REFERENCES flight_delay(delay_id) ON DELETE CASCADE,
  FOREIGN KEY (flight_id)       REFERENCES flight(flight_id) ON DELETE CASCADE,
  FOREIGN KEY (cause_flight_id) REFERENCES flight(flight_id) ON DELETE SET NULL,
  INDEX idx_impact_delay (delay_id, pass_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Scratch table for simulate_delay(): candidate delays per pass. A regular table,
-- not TEMPORARY, because MySQL can't open a TEMPORARY table twice in one
-- statement (error 1137) and the engine joins it to itself. See DEVIATIONS.md.
CREATE TABLE cascade_candidate (
  flight_id        INT NOT NULL,
  cause_flight_id  INT NULL,
  link             ENUM('AIRCRAFT','CREW','GATE','SLOT') NOT NULL,
  required_delay   INT NOT NULL,
  INDEX idx_cand_flight (flight_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE ticket (
  ticket_id      INT AUTO_INCREMENT PRIMARY KEY,
  booking_id     INT NOT NULL,
  flight_id      INT NOT NULL,
  seat_no        VARCHAR(4) NOT NULL,
  fare           DECIMAL(10,2) NOT NULL CHECK (fare >= 0),
  class          ENUM('ECONOMY','PREMIUM','BUSINESS','FIRST') NOT NULL,
  issued_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  checked_in_at  TIMESTAMP NULL,
  boarded_at     TIMESTAMP NULL,
  UNIQUE KEY uq_ticket_seat (flight_id, seat_no),
  FOREIGN KEY (booking_id) REFERENCES booking(booking_id) ON DELETE CASCADE,
  FOREIGN KEY (flight_id)  REFERENCES flight(flight_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SET FOREIGN_KEY_CHECKS = 1;
````

### A.3 `database/02_seed_reference.sql`

````sql
-- 20 airports (insert order fixes airport_id 1=DEL .. 20=VNS, relied on by
-- 03_seed_operational.sql). 1-6 are hubs: 24h, more gates, bigger MCT.
-- Some spokes have a night curfew (open_time/close_time).
-- runway_slots_per_hour is tightened to each airport's real peak after the
-- schedule is generated (end of 03_seed_operational.sql).
INSERT INTO airport (iata_code, icao_code, city, country, timezone,
                     open_time, close_time, runway_slots_per_hour, min_connect_min, min_turnaround_min) VALUES
('DEL','VIDP','Delhi','India','Asia/Kolkata',          NULL, NULL, 12, 75, 60),
('BOM','VABB','Mumbai','India','Asia/Kolkata',         NULL, NULL, 10, 75, 60),
('BLR','VOBL','Bengaluru','India','Asia/Kolkata',      NULL, NULL, 10, 60, 55),
('MAA','VOMM','Chennai','India','Asia/Kolkata',        NULL, NULL,  8, 60, 50),
('CCU','VECC','Kolkata','India','Asia/Kolkata',        NULL, NULL,  8, 60, 50),
('HYD','VOHS','Hyderabad','India','Asia/Kolkata',      NULL, NULL,  8, 60, 50),
('PNQ','VAPO','Pune','India','Asia/Kolkata',           '06:00:00', '23:00:00', 4, 45, 45),
('GOI','VOGO','Goa','India','Asia/Kolkata',            '06:00:00', '23:30:00', 4, 45, 45),
('AMD','VAAH','Ahmedabad','India','Asia/Kolkata',      NULL, NULL,  6, 45, 45),
('COK','VOCI','Kochi','India','Asia/Kolkata',          NULL, NULL,  6, 45, 45),
('LKO','VILK','Lucknow','India','Asia/Kolkata',        NULL, NULL,  4, 45, 45),
('JAI','VIJP','Jaipur','India','Asia/Kolkata',         NULL, NULL,  4, 45, 45),
('TRV','VOTV','Thiruvananthapuram','India','Asia/Kolkata', NULL, NULL, 4, 45, 45),
('IXC','VICG','Chandigarh','India','Asia/Kolkata',     '06:00:00', '22:30:00', 3, 45, 45),
('PAT','VEPT','Patna','India','Asia/Kolkata',          '06:00:00', '22:30:00', 3, 45, 45),
('BBI','VEBS','Bhubaneswar','India','Asia/Kolkata',    NULL, NULL,  4, 45, 45),
('GAU','VEGT','Guwahati','India','Asia/Kolkata',       NULL, NULL,  4, 45, 45),
('NAG','VANP','Nagpur','India','Asia/Kolkata',         NULL, NULL,  4, 45, 45),
('IXB','VEBD','Bagdogra','India','Asia/Kolkata',       '06:00:00', '21:30:00', 3, 45, 45),
('VNS','VEBN','Varanasi','India','Asia/Kolkata',       '06:00:00', '22:30:00', 3, 45, 45);

-- Gates: 14 per hub across two terminals, 6 per spoke.
INSERT INTO gate (airport_id, gate_code, terminal)
WITH RECURSIVE seq AS (SELECT 1 AS n UNION ALL SELECT n + 1 FROM seq WHERE n < 14)
SELECT a.airport_id,
       CONCAT(IF(a.airport_id <= 6 AND seq.n > 7, 'B', 'A'), seq.n),
       IF(a.airport_id <= 6 AND seq.n > 7, 'T2', 'T1')
FROM airport a
JOIN seq ON seq.n <= IF(a.airport_id <= 6, 14, 6);

-- 4 aircraft types
INSERT INTO aircraft_type (model, manufacturer, seat_capacity, max_range_km, cruise_speed_kmh) VALUES
('A320-200','Airbus',180,6100,830),
('A321neo','Airbus',220,7400,830),
('B737-800','Boeing',189,5765,842),
('B777-300ER','Boeing',396,13650,892);

-- 8 delay reasons, one per category
INSERT INTO delay_reason (category, description) VALUES
('WEATHER','Delay due to adverse weather conditions at origin or destination'),
('ATC','Delay due to air traffic control restrictions or slot allocation'),
('TECHNICAL','Delay due to a technical or mechanical fault on the aircraft'),
('CREW','Delay due to crew unavailability or late crew reporting'),
('SECURITY','Delay due to security screening or incident at the airport'),
('FUEL','Delay due to fuel supply or refuelling issues'),
('MAINTENANCE','Delay due to unscheduled maintenance before departure'),
('CASCADE','Delay caused by a knock-on effect from an earlier delayed flight');

-- IATA AHM 730 delay codes, mapped to the 8 categories above
-- (reason_id: 1 WEATHER, 2 ATC, 3 TECHNICAL, 4 CREW, 5 SECURITY, 6 FUEL, 7 MAINTENANCE, 8 CASCADE).
INSERT INTO delay_code (iata_code, description, reason_id) VALUES
('71','Departure station weather below operating limits',1),
('72','Destination station weather below operating limits',1),
('73','En-route weather or diversion avoidance',1),
('75','De-icing of aircraft',1),
('77','Ground handling impaired by weather',1),
('81','ATC flow management - en-route demand/capacity',2),
('82','ATC staff or equipment en-route',2),
('83','ATC restriction at destination airport',2),
('84','Restriction at destination - weather',2),
('89','Restrictions at departure airport incl. runway/apron',2),
('41','Aircraft defect',3),
('44','Spares and maintenance equipment',3),
('46','Aircraft change for technical reasons',3),
('47','Standby aircraft unavailable',3),
('61','Flight plan, late completion or change',4),
('62','Operational requirements - fuel, load alteration',4),
('63','Late crew boarding or departure procedures',4),
('64','Flight deck crew shortage or sickness',4),
('65','Flight deck crew special request',4),
('66','Late cabin crew boarding',4),
('67','Cabin crew shortage or sickness',4),
('85','Mandatory security procedures',5),
('86','Immigration, customs, health',5),
('88','Airport facilities - security screening',5),
('36','Fuelling or defuelling, fuel supplier',6),
('42','Scheduled maintenance, late release',7),
('43','Non-scheduled maintenance',7),
('93','Aircraft rotation - late arrival from another flight',8),
('94','Cabin crew rotation - awaiting crew from another flight',8),
('95','Crew rotation - awaiting flight deck crew',8),
('96','Operations control - rerouting, diversion, consolidation',8);
````

### A.4 `database/03_seed_operational.sql`

````sql
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
````

### A.5 `database/04_triggers.sql`

````sql
-- NOTE: the spec originally called for a trg_cascade_delay AFTER UPDATE trigger on
-- flight that itself UPDATEs flight. MySQL rejects this at runtime with error 1442
-- ("Can't update table 'flight' in stored function/trigger because it is already
-- used by statement which invoked this stored function/trigger") -- this is a real
-- MySQL restriction, and the spec's claim that MySQL has no mutating-table problem
-- does not hold for a trigger self-modifying its own table. Worse, the original
-- design also depended on the trigger recursively re-firing itself as it updated
-- each downstream flight, to walk multi-hop chains -- MySQL does not support that
-- kind of trigger self-recursion either. The cascade is instead implemented as an
-- iterative stored procedure, simulate_delay() in 05_procedures.sql, called
-- explicitly by the "Simulate Delay" action instead of firing automatically on
-- UPDATE. See DEVIATIONS.md.

DELIMITER $$

CREATE TRIGGER trg_update_duty
AFTER UPDATE ON flight
FOR EACH ROW
BEGIN
  DECLARE v_flown DECIMAL(5,2);
  IF NEW.actual_arrival IS NOT NULL AND OLD.actual_arrival IS NULL THEN
    SET v_flown = TIMESTAMPDIFF(MINUTE, NEW.actual_departure, NEW.actual_arrival) / 60;
    INSERT INTO duty_log (crew_id, duty_date, hours_flown, hours_on_duty)
      SELECT ca.crew_id, DATE(NEW.actual_departure), v_flown, v_flown + 1
      FROM crew_assignment ca
      WHERE ca.flight_id = NEW.flight_id
        AND ca.unassigned_at IS NULL
    ON DUPLICATE KEY UPDATE
      hours_flown = hours_flown + v_flown,
      hours_on_duty = hours_on_duty + v_flown + 1;
  END IF;
END$$

CREATE TRIGGER trg_check_duty_limit
BEFORE INSERT ON crew_assignment
FOR EACH ROW
BEGIN
  DECLARE v_current_hours DECIMAL(5,2) DEFAULT 0;
  DECLARE v_flight_hours DECIMAL(5,2);
  DECLARE v_dep_date DATE;

  SELECT DATE(sched_departure),
         TIMESTAMPDIFF(MINUTE, sched_departure, sched_arrival) / 60
  INTO v_dep_date, v_flight_hours
  FROM flight WHERE flight_id = NEW.flight_id;

  SELECT COALESCE(hours_on_duty, 0) INTO v_current_hours
  FROM duty_log
  WHERE crew_id = NEW.crew_id AND duty_date = v_dep_date;

  IF v_current_hours + v_flight_hours > 11 THEN
    SIGNAL SQLSTATE '45000'
    SET MESSAGE_TEXT = 'Assignment would exceed 11-hour daily duty limit for crew member';
  END IF;
END$$

CREATE TRIGGER trg_no_double_seat
BEFORE INSERT ON ticket
FOR EACH ROW
BEGIN
  DECLARE v_count INT;
  SELECT COUNT(*) INTO v_count
  FROM ticket t
  JOIN booking b ON b.booking_id = t.booking_id
  WHERE t.flight_id = NEW.flight_id
    AND t.seat_no = NEW.seat_no
    AND b.status = 'CONFIRMED';
  IF v_count > 0 THEN
    SIGNAL SQLSTATE '45000'
    SET MESSAGE_TEXT = 'Seat already booked on this flight';
  END IF;
END$$

DELIMITER ;
````

### A.6 `database/05_procedures.sql`

````sql
DELIMITER $$

-- The four cascade rules, evaluated against current ETD/ETA. Fills
-- cascade_candidate with the delay each rule requires of every not-yet-departed
-- flight (<= current delay means the rule is satisfied). Called once per pass by
-- simulate_delay(); tests call it directly to check the schedule is consistent.
CREATE PROCEDURE compute_cascade_candidates()
BEGIN
  DELETE FROM cascade_candidate;

  -- AIRCRAFT: previous leg of the same aircraft (by schedule)
  INSERT INTO cascade_candidate (flight_id, cause_flight_id, link, required_delay)
  SELECT b.flight_id, a.flight_id, 'AIRCRAFT',
         TIMESTAMPDIFF(MINUTE, b.std, DATE_ADD(a.eta, INTERVAL ap.min_turnaround_min MINUTE))
  FROM (SELECT flight_id, std, status, origin_airport_id,
               LAG(flight_id) OVER (PARTITION BY aircraft_id ORDER BY std, flight_id) AS prev_id
        FROM v_flight_times WHERE status <> 'CANCELLED') b
  JOIN v_flight_times a ON a.flight_id = b.prev_id
  JOIN airport ap ON ap.airport_id = b.origin_airport_id
  WHERE b.status IN ('SCHEDULED', 'BOARDING');

  -- CREW: each active crew member's previous flight (by schedule)
  INSERT INTO cascade_candidate (flight_id, cause_flight_id, link, required_delay)
  SELECT b.flight_id, a.flight_id, 'CREW',
         TIMESTAMPDIFF(MINUTE, b.std, DATE_ADD(a.eta, INTERVAL 45 MINUTE))
  FROM (SELECT ft.flight_id, ft.std, ft.status,
               LAG(ft.flight_id) OVER (PARTITION BY ca.crew_id ORDER BY ft.std, ft.flight_id) AS prev_id
        FROM crew_assignment ca
        JOIN v_flight_times ft ON ft.flight_id = ca.flight_id
        WHERE ca.unassigned_at IS NULL AND ft.status <> 'CANCELLED') b
  JOIN v_flight_times a ON a.flight_id = b.prev_id
  WHERE b.status IN ('SCHEDULED', 'BOARDING');

  -- GATE: previous departure from the same gate (by schedule)
  INSERT INTO cascade_candidate (flight_id, cause_flight_id, link, required_delay)
  SELECT b.flight_id, a.flight_id, 'GATE',
         TIMESTAMPDIFF(MINUTE, b.boarding_sched, DATE_ADD(a.etd, INTERVAL 10 MINUTE))
  FROM (SELECT flight_id, status,
               COALESCE(boarding_start, DATE_SUB(std, INTERVAL 45 MINUTE)) AS boarding_sched,
               LAG(flight_id) OVER (PARTITION BY gate_id ORDER BY std, flight_id) AS prev_id
        FROM v_flight_times WHERE gate_id IS NOT NULL AND status <> 'CANCELLED') b
  JOIN v_flight_times a ON a.flight_id = b.prev_id
  WHERE b.status IN ('SCHEDULED', 'BOARDING');

  -- SLOT: departures per airport per clock hour of ETD; undelayed flights keep
  -- their slots, delayed ones beyond the limit move to the start of the next hour
  INSERT INTO cascade_candidate (flight_id, cause_flight_id, link, required_delay)
  SELECT x.flight_id, NULL, 'SLOT',
         TIMESTAMPDIFF(MINUTE, x.std, DATE_ADD(x.hour_start, INTERVAL 1 HOUR))
  FROM (SELECT ft.flight_id, ft.std, ft.status, ap.runway_slots_per_hour AS cap,
               TIMESTAMP(DATE(ft.etd), MAKETIME(HOUR(ft.etd), 0, 0)) AS hour_start,
               ROW_NUMBER() OVER (PARTITION BY ft.origin_airport_id, DATE(ft.etd), HOUR(ft.etd)
                                  ORDER BY ft.delay_minutes > 0, ft.etd, ft.flight_id) AS slot_rank
        FROM v_flight_times ft
        JOIN airport ap ON ap.airport_id = ft.origin_airport_id
        WHERE ft.status <> 'CANCELLED') x
  WHERE x.slot_rank > x.cap AND x.status IN ('SCHEDULED', 'BOARDING');
END$$

-- P0: File a delay notice on a flight and cascade it across the whole operation.
-- Implemented as a stored procedure (not a trigger) -- see the note in
-- 04_triggers.sql for why.
--
-- After applying the notice to the flight itself, each pass of the WHILE loop
-- asks four rules what delay every not-yet-departed flight now *requires*:
--   AIRCRAFT  next leg of the same aircraft can't leave before it lands + turnaround
--   CREW      a crew member's next flight can't leave before their previous one
--             lands + 45 min crew connection
--   GATE      the next flight at a gate can't start boarding until the previous
--             one has pushed back + 10 min
--   SLOT      an airport can't exceed runway_slots_per_hour departures in a clock
--             hour; delayed flights beyond the limit move to the next hour
-- The biggest requirement per flight wins, is logged to delay_impact, and raises
-- delay_minutes. The loop stops when a pass changes nothing. delay_minutes only
-- ever increases, so it terminates; the 50-pass cap is a backstop.
--
-- Estimated times are never stored: ETD/ETA = scheduled + delay_minutes (see
-- v_flight_times in 06_views.sql).
CREATE PROCEDURE simulate_delay(
  IN p_flight_id INT,
  IN p_minutes INT,
  IN p_code_id INT,
  IN p_sub_reason VARCHAR(200),
  IN p_phase VARCHAR(20),
  IN p_ops_status VARCHAR(10),
  IN p_new_gate_id INT,
  IN p_new_boarding DATETIME,
  IN p_pax_deboarded BOOLEAN,
  IN p_swap_aircraft_id INT,
  IN p_announcement VARCHAR(500),
  IN p_meal_voucher BOOLEAN,
  IN p_compensation BOOLEAN,
  IN p_rebooking BOOLEAN,
  IN p_reported_by VARCHAR(80),
  IN p_remarks VARCHAR(500),
  OUT p_delay_id INT
)
BEGIN
  DECLARE v_changed INT DEFAULT 1;
  DECLARE v_pass INT DEFAULT 0;
  DECLARE v_status VARCHAR(10);
  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  START TRANSACTION;

  SELECT status INTO v_status FROM flight WHERE flight_id = p_flight_id FOR UPDATE;
  IF v_status IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Flight not found';
  END IF;
  IF v_status IN ('ARRIVED', 'CANCELLED', 'DIVERTED') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Cannot delay a flight that has arrived, diverted or been cancelled';
  END IF;

  INSERT INTO flight_delay (
    flight_id, code_id, minutes, sub_reason, phase, ops_status,
    new_gate_id, new_boarding_time, pax_deboarded, swap_aircraft_id,
    announcement, meal_voucher, compensation_eligible, rebooking_offered,
    reported_by, remarks)
  SELECT p_flight_id, dc.code_id, p_minutes, p_sub_reason, p_phase, p_ops_status,
         p_new_gate_id, p_new_boarding, p_pax_deboarded, p_swap_aircraft_id,
         p_announcement, p_meal_voucher, p_compensation, p_rebooking,
         p_reported_by, p_remarks
  FROM delay_code dc WHERE dc.code_id = p_code_id;
  IF ROW_COUNT() = 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Unknown delay code';
  END IF;
  SET p_delay_id = LAST_INSERT_ID();

  UPDATE flight
  SET delay_minutes = delay_minutes + p_minutes,
      gate_id = COALESCE(p_new_gate_id, gate_id),
      aircraft_id = COALESCE(p_swap_aircraft_id, aircraft_id),
      status = IF(p_ops_status = 'CANCELLED', 'CANCELLED', status)
  WHERE flight_id = p_flight_id;

  -- A cancelled flight doesn't push anything downstream.
  IF p_ops_status = 'CANCELLED' THEN
    SET v_changed = 0;
  END IF;

  WHILE v_changed > 0 AND v_pass < 50 DO
    SET v_pass = v_pass + 1;
    CALL compute_cascade_candidates();

    -- Winning (largest) requirement per flight, where it exceeds the current delay
    INSERT INTO delay_impact (delay_id, flight_id, cause_flight_id, link, minutes_added, old_etd, new_etd, pass_no)
    SELECT p_delay_id, w.flight_id, w.cause_flight_id, w.link,
           w.required_delay - f.delay_minutes,
           DATE_ADD(f.sched_departure, INTERVAL f.delay_minutes MINUTE),
           DATE_ADD(f.sched_departure, INTERVAL w.required_delay MINUTE),
           v_pass
    FROM (SELECT c.*, ROW_NUMBER() OVER (PARTITION BY c.flight_id ORDER BY c.required_delay DESC, c.link) AS rn
          FROM cascade_candidate c) w
    JOIN flight f ON f.flight_id = w.flight_id
    WHERE w.rn = 1 AND w.required_delay > f.delay_minutes;

    UPDATE flight f
    JOIN delay_impact di ON di.flight_id = f.flight_id AND di.delay_id = p_delay_id AND di.pass_no = v_pass
    SET f.delay_minutes = f.delay_minutes + di.minutes_added,
        f.parent_flight_id = COALESCE(di.cause_flight_id, f.parent_flight_id);

    SET v_changed = ROW_COUNT();
  END WHILE;

  DELETE FROM cascade_candidate;
  COMMIT;
END$$

-- Undo every filed delay so the demo can be run again. Gate changes and
-- aircraft swaps made by notices are not reverted (the originals aren't kept);
-- re-run scripts/setup_db.sh for a full reset.
CREATE PROCEDURE reset_all_delays()
BEGIN
  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;
  START TRANSACTION;
  DELETE FROM flight_delay;  -- delay_impact rows go with it (ON DELETE CASCADE)
  UPDATE flight
  SET delay_minutes = 0,
      parent_flight_id = NULL,
      status = IF(status = 'CANCELLED', 'SCHEDULED', status)
  WHERE delay_minutes <> 0 OR parent_flight_id IS NOT NULL OR status = 'CANCELLED';
  COMMIT;
END$$

-- P1: Recursive cascade trace using CTE (MySQL 8.0+)
CREATE PROCEDURE analyse_cascade(IN p_flight_id INT)
BEGIN
  WITH RECURSIVE cascade_tree AS (
    SELECT flight_id, flight_number, parent_flight_id,
           sched_departure, delay_minutes, 0 AS cascade_depth
    FROM flight
    WHERE flight_id = p_flight_id
    UNION ALL
    SELECT f.flight_id, f.flight_number, f.parent_flight_id,
           f.sched_departure, f.delay_minutes, ct.cascade_depth + 1
    FROM flight f
    INNER JOIN cascade_tree ct ON f.parent_flight_id = ct.flight_id
  )
  SELECT * FROM cascade_tree ORDER BY cascade_depth, sched_departure;
END$$

-- P2: Find eligible replacement crew for a given flight
CREATE PROCEDURE find_replacement_crew(IN p_flight_id INT)
BEGIN
  DECLARE v_type_id INT;
  DECLARE v_origin_id INT;
  DECLARE v_sched_dep DATETIME;
  DECLARE v_sched_arr DATETIME;

  SELECT a.type_id, r.origin_airport_id, f.sched_departure, f.sched_arrival
  INTO v_type_id, v_origin_id, v_sched_dep, v_sched_arr
  FROM flight f
  JOIN aircraft a ON a.aircraft_id = f.aircraft_id
  JOIN route r ON r.route_id = f.route_id
  WHERE f.flight_id = p_flight_id;

  SELECT c.crew_id, c.name, c.role
  FROM crew c
  JOIN crew_certification cc ON cc.crew_id = c.crew_id
  WHERE cc.type_id = v_type_id
    AND cc.expiry_date > CURDATE()
    AND c.base_airport_id = v_origin_id
    AND c.terminated_at IS NULL
    AND NOT EXISTS (
      SELECT 1 FROM crew_assignment ca
      JOIN flight f2 ON f2.flight_id = ca.flight_id
      WHERE ca.crew_id = c.crew_id
        AND ca.unassigned_at IS NULL
        AND f2.sched_departure < v_sched_arr
        AND f2.sched_arrival > v_sched_dep
    )
    AND COALESCE(
      (SELECT hours_on_duty FROM duty_log
       WHERE crew_id = c.crew_id AND duty_date = DATE(v_sched_dep)),
      0
    ) < 8;
END$$

-- P3: Transactional ticket booking
CREATE PROCEDURE book_ticket(
  IN p_passenger_id INT,
  IN p_flight_id INT,
  IN p_seat_no VARCHAR(4),
  IN p_class VARCHAR(10),
  IN p_fare DECIMAL(10,2),
  OUT p_pnr CHAR(6)
)
BEGIN
  DECLARE v_booking_id INT;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  START TRANSACTION;

  -- MD5()/SHA1() are unavailable on MySQL builds linked against an OpenSSL 3.x
  -- "default" provider with the legacy provider disabled (common on Homebrew
  -- installs) -- calling either raises "FUNCTION db.MD5 does not exist" even
  -- though the function exists on a standard build. UUID() has no such
  -- dependency and is equally suitable for generating a random PNR. See
  -- DEVIATIONS.md.
  SET p_pnr = UPPER(SUBSTRING(REPLACE(UUID(), '-', ''), 1, 6));

  INSERT INTO booking (pnr, passenger_id, status)
  VALUES (p_pnr, p_passenger_id, 'CONFIRMED');
  SET v_booking_id = LAST_INSERT_ID();

  INSERT INTO ticket (booking_id, flight_id, seat_no, fare, class)
  VALUES (v_booking_id, p_flight_id, p_seat_no, p_fare, p_class);

  COMMIT;
END$$

DELIMITER ;
````

### A.7 `database/06_views.sql`

````sql
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
````

### A.8 `database/07_seed_delays.sql`

````sql
-- Sample delay notices filed through simulate_delay(), so reports and the
-- delay log have data out of the box. Flights are picked by aircraft, day
-- offset and leg so the file doesn't depend on flight_id values.

SET @f = (SELECT flight_id FROM flight WHERE aircraft_id = 3 AND DATE(sched_departure) = CURDATE() + INTERVAL 2 DAY ORDER BY sched_departure LIMIT 0, 1);
CALL simulate_delay(@f, 95, (SELECT code_id FROM delay_code WHERE iata_code = '71'), 'Dense fog at DEL, RVR below CAT I minima', 'PRE_BOARDING', 'DELAYED', NULL, NULL, FALSE, NULL, 'Due to dense fog, departure is delayed. We regret the inconvenience.', FALSE, FALSE, FALSE, 'R. Mehta (DM DEL)', 'Fog forecast to lift by 09:00', @d);
SET @f = (SELECT flight_id FROM flight WHERE aircraft_id = 8 AND DATE(sched_departure) = CURDATE() + INTERVAL 2 DAY ORDER BY sched_departure LIMIT 2, 1);
CALL simulate_delay(@f, 40, (SELECT code_id FROM delay_code WHERE iata_code = '81'), 'Flow restriction over Nagpur FIR', 'AT_GATE', 'DELAYED', NULL, NULL, FALSE, NULL, 'ATC restrictions have delayed departure. Please remain near the gate.', FALSE, FALSE, FALSE, 'S. Iyer (OCC)', NULL, @d);
SET @f = (SELECT flight_id FROM flight WHERE aircraft_id = 11 AND DATE(sched_departure) = CURDATE() + INTERVAL 3 DAY ORDER BY sched_departure LIMIT 0, 1);
CALL simulate_delay(@f, 150, (SELECT code_id FROM delay_code WHERE iata_code = '41'), 'Hydraulic system B low pressure on pre-flight check', 'AT_GATE', 'ON_HOLD', NULL, NULL, FALSE, NULL, 'A technical check is in progress. A new departure time will be announced shortly.', TRUE, FALSE, FALSE, 'A. Khan (MCC)', 'AOG spares requested from base', @d);
SET @f = (SELECT flight_id FROM flight WHERE aircraft_id = 14 AND DATE(sched_departure) = CURDATE() + INTERVAL 3 DAY ORDER BY sched_departure LIMIT 1, 1);
CALL simulate_delay(@f, 30, (SELECT code_id FROM delay_code WHERE iata_code = '63'), 'Late crew reporting after rest-period dispute', 'PRE_BOARDING', 'DELAYED', NULL, NULL, FALSE, NULL, 'Departure delayed due to operational reasons.', FALSE, FALSE, FALSE, 'P. Nair (Crew Control)', NULL, @d);
SET @f = (SELECT flight_id FROM flight WHERE aircraft_id = 19 AND DATE(sched_departure) = CURDATE() + INTERVAL 4 DAY ORDER BY sched_departure LIMIT 0, 1);
CALL simulate_delay(@f, 60, (SELECT code_id FROM delay_code WHERE iata_code = '85'), 'Unattended bag in security hold area', 'PRE_BOARDING', 'DELAYED', NULL, NULL, FALSE, NULL, 'Security checks at the airport have delayed boarding.', FALSE, FALSE, FALSE, 'K. Rao (DM)', NULL, @d);
SET @f = (SELECT flight_id FROM flight WHERE aircraft_id = 22 AND DATE(sched_departure) = CURDATE() + INTERVAL 4 DAY ORDER BY sched_departure LIMIT 2, 1);
CALL simulate_delay(@f, 75, (SELECT code_id FROM delay_code WHERE iata_code = '36'), 'Fuel bowser breakdown at stand', 'AT_GATE', 'DELAYED', NULL, NULL, FALSE, NULL, 'Refuelling delay. We will board shortly.', FALSE, FALSE, FALSE, 'D. Das (Ramp)', 'Second bowser dispatched', @d);
SET @f = (SELECT flight_id FROM flight WHERE aircraft_id = 27 AND DATE(sched_departure) = CURDATE() + INTERVAL 5 DAY ORDER BY sched_departure LIMIT 0, 1);
CALL simulate_delay(@f, 200, (SELECT code_id FROM delay_code WHERE iata_code = '43'), 'Bird strike inspection after previous sector', 'PRE_BOARDING', 'DELAYED', NULL, NULL, FALSE, NULL, 'Aircraft inspection required. Meal vouchers are available at the counter.', TRUE, TRUE, TRUE, 'V. Menon (MCC)', 'Engine borescope inspection', @d);
SET @f = (SELECT flight_id FROM flight WHERE aircraft_id = 30 AND DATE(sched_departure) = CURDATE() + INTERVAL 5 DAY ORDER BY sched_departure LIMIT 4, 1);
CALL simulate_delay(@f, 45, (SELECT code_id FROM delay_code WHERE iata_code = '93'), 'Inbound aircraft late from previous rotation', 'PRE_BOARDING', 'DELAYED', NULL, NULL, FALSE, NULL, 'Your aircraft is arriving late from its previous flight.', FALSE, FALSE, FALSE, 'S. Iyer (OCC)', NULL, @d);
SET @f = (SELECT flight_id FROM flight WHERE aircraft_id = 35 AND DATE(sched_departure) = CURDATE() + INTERVAL 6 DAY ORDER BY sched_departure LIMIT 0, 1);
CALL simulate_delay(@f, 120, (SELECT code_id FROM delay_code WHERE iata_code = '72'), 'Thunderstorms at destination, holding expected', 'PRE_BOARDING', 'DELAYED', NULL, NULL, FALSE, NULL, 'Weather at the destination has delayed departure.', TRUE, FALSE, FALSE, 'R. Mehta (DM DEL)', NULL, @d);
SET @f = (SELECT flight_id FROM flight WHERE aircraft_id = 38 AND DATE(sched_departure) = CURDATE() + INTERVAL 6 DAY ORDER BY sched_departure LIMIT 2, 1);
CALL simulate_delay(@f, 35, (SELECT code_id FROM delay_code WHERE iata_code = '89'), 'Runway 27 closed for friction testing', 'TAXI', 'DELAYED', NULL, NULL, FALSE, NULL, 'Runway restrictions have delayed departure.', FALSE, FALSE, FALSE, 'A. Gupta (ATC liaison)', NULL, @d);
````

### A.9 `database/queries/q1_cascade_trace.sql`

````sql
-- Recursive cascade trace: every flight downstream of a delayed flight, via parent_flight_id.
-- Example below is for flight_id = 1; the app calls the equivalent stored procedure analyse_cascade(:flight_id).
WITH RECURSIVE cascade_tree AS (
  SELECT flight_id, flight_number, parent_flight_id,
         sched_departure, delay_minutes, 0 AS cascade_depth
  FROM flight
  WHERE flight_id = 1
  UNION ALL
  SELECT f.flight_id, f.flight_number, f.parent_flight_id,
         f.sched_departure, f.delay_minutes, ct.cascade_depth + 1
  FROM flight f
  INNER JOIN cascade_tree ct ON f.parent_flight_id = ct.flight_id
)
SELECT * FROM cascade_tree ORDER BY cascade_depth, sched_departure;
````

### A.10 `database/queries/q2_replacement_crew.sql`

````sql
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
````

### A.11 `database/queries/q3_ontime_performance.sql`

````sql
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
````

### A.12 `database/queries/q4_top_delay_causes.sql`

````sql
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
````

### A.13 `database/queries/q5_cascade_passengers.sql`

````sql
-- Passengers affected by a cascade rooted at a given flight.
-- Example below is for flight_id = 1.
WITH RECURSIVE cascade_tree AS (
  SELECT flight_id FROM flight WHERE flight_id = 1
  UNION ALL
  SELECT f.flight_id FROM flight f
  JOIN cascade_tree ct ON f.parent_flight_id = ct.flight_id
)
SELECT DISTINCT p.passenger_id, p.name, p.email, t.flight_id, t.seat_no, t.class
FROM cascade_tree ct
JOIN ticket t ON t.flight_id = ct.flight_id
JOIN booking b ON b.booking_id = t.booking_id AND b.status = 'CONFIRMED'
JOIN passenger p ON p.passenger_id = b.passenger_id
ORDER BY t.flight_id, p.name;
````

### A.14 `database/queries/q6_load_factor.sql`

````sql
-- Load factor (tickets sold / seat capacity) per flight, excluding cancelled bookings.
SELECT
  f.flight_id, f.flight_number, f.sched_departure,
  at.seat_capacity,
  COUNT(t.ticket_id) AS tickets_sold,
  ROUND(100 * COUNT(t.ticket_id) / at.seat_capacity, 1) AS load_factor_pct
FROM flight f
JOIN aircraft a ON a.aircraft_id = f.aircraft_id
JOIN aircraft_type at ON at.type_id = a.type_id
LEFT JOIN (
  SELECT t.ticket_id, t.flight_id
  FROM ticket t
  JOIN booking b ON b.booking_id = t.booking_id
  WHERE b.status <> 'CANCELLED'
) t ON t.flight_id = f.flight_id
GROUP BY f.flight_id, f.flight_number, f.sched_departure, at.seat_capacity
ORDER BY f.sched_departure;
````

### A.15 `database/queries/q7_duty_status.sql`

````sql
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
````

### A.16 `database/queries/q8_aircraft_utilisation.sql`

````sql
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
````

### A.17 `database/setup.sql`

````sql
-- Run with: mysql -u root -p airline_cascades < setup.sql  (from inside database/)
SOURCE 01_schema.sql;
SOURCE 02_seed_reference.sql;
SOURCE 03_seed_operational.sql;
SOURCE 04_triggers.sql;
SOURCE 05_procedures.sql;
SOURCE 06_views.sql;
SOURCE 07_seed_delays.sql;
````

### A.18 `app.py`

````python
from flask import Flask, render_template
import mysql.connector

from src.config import Settings
from src.db import query
from src.services.lookups import enum_values
from src.routes import (
    admin,
    airports,
    bookings,
    cascade,
    crew,
    dashboard,
    delays,
    flights,
    passengers,
    reports,
    schema,
)


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Settings)

    app.register_blueprint(dashboard.bp)
    app.register_blueprint(flights.bp, url_prefix="/flights")
    app.register_blueprint(cascade.bp, url_prefix="/cascade")
    app.register_blueprint(crew.bp, url_prefix="/crew")
    app.register_blueprint(passengers.bp, url_prefix="/passengers")
    app.register_blueprint(bookings.bp, url_prefix="/bookings")
    app.register_blueprint(reports.bp, url_prefix="/reports")
    app.register_blueprint(admin.bp, url_prefix="/admin")
    app.register_blueprint(schema.bp, url_prefix="/schema")
    app.register_blueprint(delays.bp, url_prefix="/delays")
    app.register_blueprint(airports.bp, url_prefix="/airports")

    app.jinja_env.globals["enum_values"] = enum_values

    @app.errorhandler(mysql.connector.Error)
    def database_error(err):
        """A table was changed by hand in a way this page depends on (a dropped or
        renamed column, a missing table...). Say exactly what MySQL reported."""
        return render_template("error.html", title="The database rejected this page",
                               message=err.msg, code=err.errno), 500

    @app.errorhandler(404)
    def not_found(err):
        return render_template("error.html", title="Nothing here",
                               message="That page or record doesn't exist. It may have been deleted.", code=404), 404

    @app.context_processor
    def nav_counts():
        """Late-flight count shown in the nav on every page. If the flight table
        has been altered so this can't run, the nav just omits it (the page's own
        error, if any, is reported by database_error)."""
        try:
            return {"delayed_now": query(
                "SELECT COUNT(*) AS n FROM flight WHERE delay_minutes > 0 AND status IN ('SCHEDULED', 'BOARDING', 'DEPARTED')"
            )[0]["n"]}
        except mysql.connector.Error:
            return {"delayed_now": 0}

    @app.template_filter("human")
    def human(value):
        """Database enum values for display: FIRST_OFFICER -> First officer, ATC stays ATC."""
        if not value:
            return value
        text = str(value)
        return text if len(text) <= 3 else text.replace("_", " ").capitalize()

    @app.template_filter("when")
    def when(value):
        """Datetimes as 'Wed 23 Sep, 18:28'; dates as 'Wed 23 Sep 2026'; anything else unchanged."""
        if hasattr(value, "hour"):
            return value.strftime("%a %d %b, %H:%M")
        if hasattr(value, "strftime"):
            return value.strftime("%a %d %b %Y")
        return value

    @app.template_filter("hhmm")
    def hhmm(value):
        """Formats datetimes and MySQL TIME values (timedeltas) as HH:MM."""
        if value is None:
            return ""
        if hasattr(value, "strftime"):
            return value.strftime("%H:%M")
        minutes = int(value.total_seconds()) // 60
        return f"{minutes // 60:02d}:{minutes % 60:02d}"

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
````

### A.19 `src/__init__.py`

````python

````

### A.20 `src/config.py`

````python
import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = int(os.environ.get("DB_PORT", 3306))
    DB_USER = os.environ.get("DB_USER", "root")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
    DB_NAME = os.environ.get("DB_NAME", "airline_cascades")
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-cia3")
````

### A.21 `src/db.py`

````python
from contextlib import contextmanager

import mysql.connector.pooling

from src.config import Settings

_pool = None


def init_pool():
    global _pool
    _pool = mysql.connector.pooling.MySQLConnectionPool(
        pool_name="airline_pool",
        pool_size=10,
        host=Settings.DB_HOST,
        port=Settings.DB_PORT,
        user=Settings.DB_USER,
        password=Settings.DB_PASSWORD,
        database=Settings.DB_NAME,
        autocommit=False,
    )


@contextmanager
def get_conn():
    global _pool
    if _pool is None:
        init_pool()
    conn = _pool.get_connection()
    try:
        yield conn
    finally:
        conn.close()


def query(sql, params=None):
    with get_conn() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params or ())
        rows = cursor.fetchall()
        cursor.close()
        return rows


def execute(sql, params=None):
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params or ())
        conn.commit()
        lastrowid = cursor.lastrowid
        cursor.close()
        return lastrowid


def call_proc_with_out(proc_name, args):
    """Call a stored procedure that has OUT/INOUT params and return the
    resolved args tuple (used by book_ticket's OUT p_pnr)."""
    with get_conn() as conn:
        cursor = conn.cursor()
        result = cursor.callproc(proc_name, args)
        cursor.close()
        conn.commit()
        return result


def call_proc(proc_name, args=None):
    """Call a stored procedure and return all result sets (list of list-of-dict)."""
    with get_conn() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.callproc(proc_name, args or ())
        result_sets = []
        for result in cursor.stored_results():
            result_sets.append(result.fetchall())
        cursor.close()
        conn.commit()
        return result_sets
````

### A.22 `src/routes/__init__.py`

````python

````

### A.23 `src/routes/admin.py`

````python
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort

from src.routes.helpers import db_action
from src.services import admin as admin_service

bp = Blueprint("admin", __name__)


def _require_entity(entity):
    if entity not in admin_service.ENTITIES:
        abort(404)
    return admin_service.ENTITIES[entity]


def _fk_options(flds):
    return {f["name"]: admin_service.fk_options(f["ref"]) for f in flds if f["type"] == "fk"}


@bp.route("/")
def index():
    return render_template("admin/index.html", entities=admin_service.ENTITIES)


def _name(cfg):
    item = cfg["item"]
    return item[0].upper() + item[1:]


@bp.route("/<entity>/")
def list_view(entity):
    cfg = _require_entity(entity)
    flds = admin_service.fields(entity)
    return render_template(
        "admin/list.html", entity=entity, cfg=cfg, fields=flds, rows=admin_service.list_rows(entity, flds)
    )


@bp.route("/<entity>/new", methods=["GET", "POST"])
def new(entity):
    cfg = _require_entity(entity)
    flds = admin_service.fields(entity)
    if request.method == "POST":
        with db_action(f"{_name(cfg)} created"):
            admin_service.create_row(entity, request.form, flds)
        return redirect(url_for("admin.list_view", entity=entity))
    return render_template(
        "admin/form.html", entity=entity, cfg=cfg, fields=flds, row=None, fk_options=_fk_options(flds)
    )


@bp.route("/<entity>/<int:row_id>/edit", methods=["GET", "POST"])
def edit(entity, row_id):
    cfg = _require_entity(entity)
    flds = admin_service.fields(entity)
    row = admin_service.get_row(entity, row_id, flds)
    if not row:
        flash("Not found", "error")
        return redirect(url_for("admin.list_view", entity=entity))
    if request.method == "POST":
        with db_action(f"{_name(cfg)} updated"):
            admin_service.update_row(entity, row_id, request.form, flds)
        return redirect(url_for("admin.list_view", entity=entity))
    return render_template(
        "admin/form.html", entity=entity, cfg=cfg, fields=flds, row=row, fk_options=_fk_options(flds)
    )


@bp.route("/<entity>/<int:row_id>/delete", methods=["POST"])
def delete(entity, row_id):
    _require_entity(entity)
    with db_action(f"{_name(admin_service.ENTITIES[entity])} deleted"):
        admin_service.delete_row(entity, row_id)
    return redirect(url_for("admin.list_view", entity=entity))
````

### A.24 `src/routes/airports.py`

````python
from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for, flash

from src.services import airports as airports_service

bp = Blueprint("airports", __name__)


@bp.route("/")
def list_view():
    return render_template("airports/list.html", airports=airports_service.list_airports())


@bp.route("/<int:airport_id>/board")
def board(airport_id):
    airport = airports_service.get_airport(airport_id)
    if not airport:
        flash("Airport not found", "error")
        return redirect(url_for("airports.list_view"))
    day = request.args.get("date") or date.today().isoformat()
    return render_template(
        "airports/board.html",
        airport=airport,
        day=day,
        dates=airports_service.board_dates(),
        departures=airports_service.departures(airport_id, day),
        arrivals=airports_service.arrivals(airport_id, day),
    )
````

### A.25 `src/routes/bookings.py`

````python
from flask import Blueprint, render_template, request, redirect, url_for, flash
import mysql.connector

from src.routes.helpers import db_action
from src.services import bookings as bookings_service
from src.services import passengers as passengers_service
from src.services import flights as flights_service
from src.services import schema_info

bp = Blueprint("bookings", __name__)


@bp.route("/")
def list_view():
    status = request.args.get("status") or None
    return render_template(
        "bookings/list.html", bookings=bookings_service.list_bookings(status=status), status=status
    )


@bp.route("/<int:booking_id>")
def detail(booking_id):
    booking = bookings_service.get_booking(booking_id)
    if not booking:
        flash("Booking not found", "error")
        return redirect(url_for("bookings.list_view"))
    return render_template(
        "bookings/detail.html",
        booking=booking,
        tickets=bookings_service.tickets_for_booking(booking_id),
        flights=flights_service.list_flights(),
        record=schema_info.record("booking", "booking_id", booking_id),
    )


@bp.route("/new", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        try:
            booking_id = bookings_service.book_ticket(
                request.form["passenger_id"],
                request.form["flight_id"],
                request.form["seat_no"],
                request.form["ticket_class"],
                request.form["fare"],
            )
            flash("Booking and ticket created", "success")
            return redirect(url_for("bookings.detail", booking_id=booking_id))
        except mysql.connector.Error as e:
            flash(f"Could not create booking: {e.msg}", "error")
    return render_template(
        "bookings/form.html",
        passengers=passengers_service.list_passengers(),
        flights=flights_service.list_flights(),
    )


@bp.route("/<int:booking_id>/cancel", methods=["POST"])
def cancel(booking_id):
    with db_action("Booking cancelled"):
        bookings_service.cancel_booking(booking_id)
    return redirect(url_for("bookings.detail", booking_id=booking_id))


@bp.route("/<int:booking_id>/ticket", methods=["POST"])
def add_ticket(booking_id):
    with db_action("Ticket added"):
        bookings_service.add_ticket(
            booking_id,
            request.form["flight_id"],
            request.form["seat_no"],
            request.form["ticket_class"],
            request.form["fare"],
        )
    return redirect(url_for("bookings.detail", booking_id=booking_id))


@bp.route("/ticket/<int:ticket_id>/checkin", methods=["POST"])
def checkin(ticket_id):
    booking_id = request.form["booking_id"]
    with db_action("Checked in"):
        bookings_service.check_in_ticket(ticket_id)
    return redirect(url_for("bookings.detail", booking_id=booking_id))
````

### A.26 `src/routes/cascade.py`

````python
from flask import Blueprint, render_template, redirect, url_for, flash

from src.services import cascade as cascade_service
from src.services import flights as flights_service

bp = Blueprint("cascade", __name__)


@bp.route("/")
def index():
    return render_template("cascade/index.html", flights=flights_service.list_flights())


@bp.route("/<int:flight_id>")
def trace(flight_id):
    flight = flights_service.get_flight(flight_id)
    if not flight:
        flash("Flight not found", "error")
        return redirect(url_for("cascade.index"))
    return render_template(
        "cascade/trace.html",
        flight=flight,
        tree=cascade_service.analyse_cascade(flight_id),
        passengers=cascade_service.affected_passengers(flight_id),
    )
````

### A.27 `src/routes/crew.py`

````python
from flask import Blueprint, render_template, request, redirect, url_for, flash

from src.routes.helpers import db_action
from src.services import crew as crew_service
from src.services import lookups
from src.services import schema_info

bp = Blueprint("crew", __name__)


@bp.route("/")
def list_view():
    role = request.args.get("role") or None
    return render_template("crew/list.html", crew=crew_service.list_crew(role=role), role=role)


@bp.route("/duty")
def duty():
    return render_template("crew/duty.html", duty=crew_service.duty_status())


@bp.route("/replacement/<int:flight_id>")
def replacement(flight_id):
    return render_template(
        "crew/replacement.html",
        flight_id=flight_id,
        candidates=crew_service.replacement_crew(flight_id),
    )


@bp.route("/<int:crew_id>")
def detail(crew_id):
    member = crew_service.get_crew(crew_id)
    if not member:
        flash("Crew member not found", "error")
        return redirect(url_for("crew.list_view"))
    return render_template(
        "crew/detail.html",
        crew=member,
        certs=crew_service.certifications(crew_id),
        aircraft_types=lookups.aircraft_types(),
        record=schema_info.record("crew", "crew_id", crew_id),
    )


@bp.route("/new", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        with db_action("Crew member created"):
            crew_service.create_crew(request.form)
        return redirect(url_for("crew.list_view"))
    return render_template("crew/form.html", crew=None, airports=lookups.airports())


@bp.route("/<int:crew_id>/edit", methods=["GET", "POST"])
def edit(crew_id):
    member = crew_service.get_crew(crew_id)
    if not member:
        flash("Crew member not found", "error")
        return redirect(url_for("crew.list_view"))
    if request.method == "POST":
        with db_action("Crew member updated"):
            crew_service.update_crew(crew_id, request.form)
        return redirect(url_for("crew.detail", crew_id=crew_id))
    return render_template("crew/form.html", crew=member, airports=lookups.airports())


@bp.route("/<int:crew_id>/delete", methods=["POST"])
def delete(crew_id):
    with db_action("Crew member deleted"):
        crew_service.delete_crew(crew_id)
    return redirect(url_for("crew.list_view"))


@bp.route("/<int:crew_id>/certify", methods=["POST"])
def certify(crew_id):
    with db_action("Certification added"):
        crew_service.add_certification(
            crew_id,
            request.form["type_id"],
            request.form["certified_date"],
            request.form["expiry_date"],
        )
    return redirect(url_for("crew.detail", crew_id=crew_id))


@bp.route("/<int:crew_id>/certify/<int:type_id>/delete", methods=["POST"])
def decertify(crew_id, type_id):
    with db_action("Certification removed"):
        crew_service.remove_certification(crew_id, type_id)
    return redirect(url_for("crew.detail", crew_id=crew_id))
````

### A.28 `src/routes/dashboard.py`

````python
from datetime import date

from flask import Blueprint, render_template, url_for

from src.services import airports as airports_service
from src.services import dashboard as dashboard_service
from src.services import delays as delays_service

bp = Blueprint("dashboard", __name__)


@bp.route("/")
def index():
    airports = airports_service.list_airports()
    routes = dashboard_service.network_routes()
    network = [
        {"id": a["airport_id"], "iata": a["iata_code"], "city": a["city"],
         "late": a["delayed_departures"], "deps": a["departures_today"],
         "url": url_for("airports.board", airport_id=a["airport_id"])}
        for a in airports
    ]
    return render_template(
        "dashboard/index.html",
        today=date.today(),
        network=network,
        network_routes=[[r["a"], r["b"]] for r in routes],
        summary=dashboard_service.summary(),
        recent_delays=dashboard_service.recent_delays(),
        flags=delays_service.network_flags(),
        airports=airports,
    )
````

### A.29 `src/routes/delays.py`

````python
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash

from src.routes.helpers import db_action
from src.services import delays as delays_service
from src.services.lookups import enum_values
from src.services import schema_info

bp = Blueprint("delays", __name__)

FLAGS = ("pax_deboarded", "meal_voucher", "compensation_eligible", "rebooking_offered")


def _text(form, name):
    return (form.get(name) or "").strip() or None


def _int(form, name):
    value = form.get(name)
    return int(value) if value else None


def _datetime(form, name):
    value = form.get(name)
    return datetime.strptime(value, "%Y-%m-%dT%H:%M") if value else None


def editable_from_form(form):
    """The fields that can still change after a notice is filed."""
    notice = {f: _text(form, f) for f in ("sub_reason", "announcement", "reported_by", "remarks")}
    notice.update({f: f in form for f in FLAGS})
    errors = [] if notice["reported_by"] else ["Reported by is required"]
    return notice, errors


def notice_from_form(form, flight):
    """Validates the delay form. Minutes can be given directly or as a new ETD;
    the ETD wins when both are filled, since it's what the duty manager sees."""
    notice, errors = editable_from_form(form)
    try:
        notice["code_id"] = _int(form, "code_id")
        notice["new_gate_id"] = _int(form, "new_gate_id")
        notice["swap_aircraft_id"] = _int(form, "swap_aircraft_id")
        notice["new_boarding_time"] = _datetime(form, "new_boarding_time")
        new_etd = _datetime(form, "new_etd")
        if new_etd:
            notice["minutes"] = int((new_etd - flight["etd"]).total_seconds() // 60)
        else:
            notice["minutes"] = _int(form, "minutes") or 0
    except ValueError:
        return notice, errors + ["Minutes, times and selections must be valid values"]

    notice["phase"] = form.get("phase")
    notice["ops_status"] = form.get("ops_status")
    if notice["phase"] not in enum_values("flight_delay", "phase"):
        errors.append("Pick a delay phase")
    if notice["ops_status"] not in enum_values("flight_delay", "ops_status"):
        errors.append("Pick an operational status")
    if not notice["code_id"]:
        errors.append("Pick an IATA delay code")
    if notice["minutes"] < 0:
        errors.append("The new departure time can't be earlier than the current estimate")
    elif notice["minutes"] == 0 and notice["ops_status"] == "DELAYED":
        errors.append("A delay needs at least 1 minute (use ON HOLD or CANCELLED otherwise)")
    if notice["minutes"] > 24 * 60:
        errors.append("Delays over 24 hours should be filed as a cancellation")
    return notice, errors


@bp.route("/")
def list_view():
    open_only = request.args.get("open") == "1"
    return render_template(
        "delays/list.html", delays=delays_service.list_delays(open_only=open_only), open_only=open_only
    )


@bp.route("/<int:delay_id>")
def detail(delay_id):
    notice = delays_service.get_delay(delay_id)
    if not notice:
        flash("Delay notice not found", "error")
        return redirect(url_for("delays.list_view"))
    impacts = delays_service.impacts(delay_id)
    affected = {notice["flight_id"]} | {i["flight_id"] for i in impacts}
    by_link = {}
    for i in impacts:
        by_link[i["link"]] = by_link.get(i["link"], 0) + 1
    return render_template(
        "delays/detail.html",
        notice=notice,
        impacts=impacts,
        by_link=by_link,
        knock_on_minutes=sum(i["minutes_added"] for i in impacts),
        summary=delays_service.affected_summary(affected),
        record=schema_info.record("flight_delay", "delay_id", delay_id),
    )


@bp.route("/<int:delay_id>/edit", methods=["GET", "POST"])
def edit(delay_id):
    notice = delays_service.get_delay(delay_id)
    if not notice:
        flash("Delay notice not found", "error")
        return redirect(url_for("delays.list_view"))
    if request.method == "POST":
        values, errors = editable_from_form(request.form)
        for e in errors:
            flash(e, "error")
        if not errors:
            with db_action("Delay notice updated"):
                delays_service.update_notice(delay_id, values)
            return redirect(url_for("delays.detail", delay_id=delay_id))
    return render_template("delays/edit.html", notice=notice)


@bp.route("/<int:delay_id>/resolve", methods=["POST"])
def resolve(delay_id):
    with db_action("Delay marked resolved"):
        delays_service.resolve(delay_id)
    return redirect(url_for("delays.detail", delay_id=delay_id))


@bp.route("/reset", methods=["GET", "POST"])
def reset():
    if request.method == "POST":
        with db_action("All delays cleared; every flight is back on schedule"):
            delays_service.reset_all()
        return redirect(url_for("delays.list_view"))
    return render_template("delays/reset.html", count=len(delays_service.list_delays()))
````

### A.30 `src/routes/flights.py`

````python
from flask import Blueprint, render_template, request, redirect, url_for, flash
import mysql.connector

from src.routes.delays import notice_from_form
from src.routes.helpers import db_action
from src.services import delays as delays_service
from src.services import flights as flights_service
from src.services import lookups
from src.services import schema_info

bp = Blueprint("flights", __name__)


@bp.route("/")
def list_view():
    status = request.args.get("status") or None
    date = request.args.get("date") or None
    q = (request.args.get("q") or "").strip() or None
    rows = flights_service.list_flights(status=status, date=date, q=q)
    return render_template("flights/list.html", flights=rows, status=status, date=date, q=q)


@bp.route("/<int:flight_id>")
def detail(flight_id):
    flight = flights_service.get_flight(flight_id)
    if not flight:
        flash("Flight not found", "error")
        return redirect(url_for("flights.list_view"))
    return render_template(
        "flights/detail.html",
        flight=flight,
        crew=flights_service.crew_for_flight(flight_id),
        delays=flights_service.delays_for_flight(flight_id),
        knock_on=flights_service.knock_on_for_flight(flight_id),
        all_crew=lookups.crew(),
        record=schema_info.record("flight", "flight_id", flight_id),
    )


@bp.route("/new", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        if not flights_service.gate_matches_route(request.form.get("gate_id"), request.form.get("route_id")):
            flash("The gate must be at the route's departure airport", "error")
            return redirect(request.url)
        with db_action("Flight created"):
            flights_service.create_flight(request.form)
        return redirect(url_for("flights.list_view"))
    return render_template(
        "flights/form.html", flight=None, routes=lookups.routes(), aircraft=lookups.aircraft(),
        gates=lookups.gates(),
    )


@bp.route("/<int:flight_id>/edit", methods=["GET", "POST"])
def edit(flight_id):
    flight = flights_service.get_flight(flight_id)
    if not flight:
        flash("Flight not found", "error")
        return redirect(url_for("flights.list_view"))
    if request.method == "POST":
        if not flights_service.gate_matches_route(request.form.get("gate_id"), request.form.get("route_id")):
            flash("The gate must be at the route's departure airport", "error")
            return redirect(request.url)
        with db_action("Flight updated"):
            flights_service.update_flight(flight_id, request.form)
        return redirect(url_for("flights.detail", flight_id=flight_id))
    return render_template(
        "flights/form.html", flight=flight, routes=lookups.routes(), aircraft=lookups.aircraft(),
        gates=lookups.gates(),
    )


@bp.route("/<int:flight_id>/delete", methods=["POST"])
def delete(flight_id):
    with db_action("Flight deleted"):
        flights_service.delete_flight(flight_id)
    return redirect(url_for("flights.list_view"))


@bp.route("/<int:flight_id>/assign-crew", methods=["POST"])
def assign_crew(flight_id):
    with db_action("Crew assigned"):
        flights_service.assign_crew(flight_id, request.form["crew_id"], request.form["role"])
    return redirect(url_for("flights.detail", flight_id=flight_id))


@bp.route("/<int:flight_id>/unassign-crew/<int:crew_id>", methods=["POST"])
def unassign_crew(flight_id, crew_id):
    with db_action("Crew unassigned"):
        flights_service.unassign_crew(flight_id, crew_id)
    return redirect(url_for("flights.detail", flight_id=flight_id))


@bp.route("/<int:flight_id>/delay", methods=["GET", "POST"])
def delay(flight_id):
    flight = flights_service.get_flight(flight_id)
    if not flight:
        flash("Flight not found", "error")
        return redirect(url_for("flights.list_view"))
    if request.method == "POST":
        notice, errors = notice_from_form(request.form, flight)
        if not errors:
            try:
                delay_id = delays_service.file_delay(flight_id, notice)
                flash(f"Delay filed on {flight['flight_number']} and cascaded across the network", "success")
                return redirect(url_for("delays.detail", delay_id=delay_id))
            except mysql.connector.Error as e:
                errors.append(f"Database error: {e.msg}")
        for e in errors:
            flash(e, "error")
    return render_template(
        "delays/form.html",
        flight=flight,
        values=request.form,
        codes=lookups.delay_codes(),
        gates=lookups.gates(flight["origin_airport_id"]),
        aircraft=lookups.aircraft(),
        phases=lookups.enum_values("flight_delay", "phase"),
        ops_statuses=lookups.enum_values("flight_delay", "ops_status"),
    )
````

### A.31 `src/routes/helpers.py`

````python
from contextlib import contextmanager

from flask import flash
import mysql.connector


@contextmanager
def db_action(success_msg=None):
    """Runs a mutating service call, turning any DB error (FK violation,
    trigger SIGNAL, unique constraint) into a flashed message instead of a 500."""
    try:
        yield
        if success_msg:
            flash(success_msg, "success")
    except mysql.connector.Error as e:
        flash(f"Database error: {e.msg}", "error")
````

### A.32 `src/routes/passengers.py`

````python
from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for, flash

from src.routes.helpers import db_action
from src.services import passengers as passengers_service
from src.services import schema_info

bp = Blueprint("passengers", __name__)


def _validate_dob(value):
    if not value:
        return "Date of birth is required"
    if date.fromisoformat(value) >= date.today():
        return "Date of birth must be in the past"
    return None


@bp.route("/")
def list_view():
    search = request.args.get("q") or None
    return render_template(
        "passengers/list.html",
        passengers=passengers_service.list_passengers(search=search),
        search=search,
    )


@bp.route("/<int:passenger_id>")
def detail(passenger_id):
    passenger = passengers_service.get_passenger(passenger_id)
    if not passenger:
        flash("Passenger not found", "error")
        return redirect(url_for("passengers.list_view"))
    return render_template(
        "passengers/detail.html",
        passenger=passenger,
        bookings=passengers_service.bookings_for_passenger(passenger_id),
        record=schema_info.record("passenger", "passenger_id", passenger_id),
    )


@bp.route("/new", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        error = _validate_dob(request.form.get("date_of_birth"))
        if error:
            flash(error, "error")
            return render_template("passengers/form.html", passenger=None)
        with db_action("Passenger created"):
            passengers_service.create_passenger(request.form)
        return redirect(url_for("passengers.list_view"))
    return render_template("passengers/form.html", passenger=None)


@bp.route("/<int:passenger_id>/edit", methods=["GET", "POST"])
def edit(passenger_id):
    passenger = passengers_service.get_passenger(passenger_id)
    if not passenger:
        flash("Passenger not found", "error")
        return redirect(url_for("passengers.list_view"))
    if request.method == "POST":
        error = _validate_dob(request.form.get("date_of_birth"))
        if error:
            flash(error, "error")
            return render_template("passengers/form.html", passenger=passenger)
        with db_action("Passenger updated"):
            passengers_service.update_passenger(passenger_id, request.form)
        return redirect(url_for("passengers.detail", passenger_id=passenger_id))
    return render_template("passengers/form.html", passenger=passenger)


@bp.route("/<int:passenger_id>/delete", methods=["POST"])
def delete(passenger_id):
    with db_action("Passenger deleted"):
        passengers_service.delete_passenger(passenger_id)
    return redirect(url_for("passengers.list_view"))
````

### A.33 `src/routes/reports.py`

````python
from flask import Blueprint, render_template

from src.services import reports as reports_service

bp = Blueprint("reports", __name__)


@bp.route("/")
def index():
    return render_template("reports/index.html")


@bp.route("/ontime")
def ontime():
    return render_template("reports/ontime.html", rows=reports_service.ontime_performance())


@bp.route("/delay-causes")
def delay_causes():
    return render_template("reports/delay_causes.html", rows=reports_service.top_delay_causes())


@bp.route("/load-factor")
def load_factor():
    return render_template("reports/load_factor.html", rows=reports_service.load_factor())


@bp.route("/duty-status")
def duty_status():
    return render_template("reports/duty_status.html", rows=reports_service.duty_status())


@bp.route("/utilisation")
def utilisation():
    return render_template("reports/utilisation.html", rows=reports_service.aircraft_utilisation())
````

### A.34 `src/routes/schema.py`

````python
from flask import Blueprint, render_template, abort, request

from src.services import schema_info

bp = Blueprint("schema", __name__)


@bp.route("/")
def index():
    return render_template("schema/index.html", tables=schema_info.tables(), views=schema_info.views())


@bp.route("/<table_name>")
def table_detail(table_name):
    names = {t["table_name"] for t in schema_info.tables() + schema_info.views()}
    if table_name not in names:
        abort(404)
    return render_template(
        "schema/table.html",
        table_name=table_name,
        columns=schema_info.columns(table_name),
        foreign_keys=schema_info.foreign_keys(table_name),
    )


@bp.route("/<table_name>/rows")
def rows(table_name):
    names = {t["table_name"] for t in schema_info.tables() + schema_info.views()}
    if table_name not in names:
        abort(404)
    page = max(1, request.args.get("page", 1, type=int))
    cols, data, total = schema_info.rows_page(table_name, page)
    return render_template(
        "schema/rows.html", table_name=table_name, cols=cols, rows=data,
        total=total, page=page, pages=max(1, -(-total // 50)),
    )
````

### A.35 `src/services/__init__.py`

````python

````

### A.36 `src/services/admin.py`

````python
"""Table-driven CRUD for the reference/lookup entities. Table and column names
below are hardcoded config, never user input, so the f-string SQL is safe."""

from src.db import query, execute
from src.services.lookups import enum_values

ENTITIES = {
    "airport": {
        "table": "airport",
        "pk": "airport_id",
        "label": "Airports",
        "item": "airport",
        "order_by": "iata_code",
        "fields": [
            {"name": "iata_code", "type": "text", "required": True, "label": "IATA"},
            {"name": "icao_code", "type": "text", "required": False, "label": "ICAO"},
            {"name": "city", "type": "text", "required": True, "label": "City"},
            {"name": "country", "type": "text", "required": True, "label": "Country"},
            {"name": "timezone", "type": "text", "required": True, "label": "Timezone"},
            {"name": "open_time", "type": "time", "required": False, "label": "Opens (curfew)"},
            {"name": "close_time", "type": "time", "required": False, "label": "Closes (curfew)"},
            {"name": "runway_slots_per_hour", "type": "number", "required": True, "label": "Departures / hour"},
            {"name": "min_connect_min", "type": "number", "required": True, "label": "Min connection (min)"},
            {"name": "min_turnaround_min", "type": "number", "required": True, "label": "Min turnaround (min)"},
        ],
    },
    "gate": {
        "table": "gate",
        "pk": "gate_id",
        "label": "Gates",
        "item": "gate",
        "order_by": "airport_id, terminal, gate_id",
        "fields": [
            {"name": "airport_id", "type": "fk", "required": True, "label": "Airport", "ref": "airport"},
            {"name": "gate_code", "type": "text", "required": True, "label": "Gate"},
            {"name": "terminal", "type": "text", "required": True, "label": "Terminal"},
        ],
    },
    "aircraft_type": {
        "table": "aircraft_type",
        "pk": "type_id",
        "label": "Aircraft Types",
        "item": "aircraft type",
        "order_by": "manufacturer, model",
        "fields": [
            {"name": "model", "type": "text", "required": True, "label": "Model"},
            {"name": "manufacturer", "type": "text", "required": True, "label": "Manufacturer"},
            {"name": "seat_capacity", "type": "number", "required": True, "label": "Seat Capacity"},
            {"name": "max_range_km", "type": "number", "required": True, "label": "Max Range (km)"},
            {"name": "cruise_speed_kmh", "type": "number", "required": False, "label": "Cruise Speed (km/h)"},
        ],
    },
    "delay_reason": {
        "table": "delay_reason",
        "pk": "reason_id",
        "label": "Delay Reasons",
        "item": "delay reason",
        "order_by": "category",
        "fields": [
            {
                "name": "category",
                "type": "select",
                "required": True,
                "label": "Category",
                "options": ["WEATHER", "ATC", "TECHNICAL", "CREW", "SECURITY", "FUEL", "MAINTENANCE", "CASCADE"],
            },
            {"name": "description", "type": "text", "required": True, "label": "Description"},
        ],
    },
    "delay_code": {
        "table": "delay_code",
        "pk": "code_id",
        "label": "IATA Delay Codes",
        "item": "IATA delay code",
        "order_by": "iata_code",
        "fields": [
            {"name": "iata_code", "type": "text", "required": True, "label": "Code"},
            {"name": "description", "type": "text", "required": True, "label": "Description"},
            {"name": "reason_id", "type": "fk", "required": True, "label": "Category", "ref": "delay_reason"},
        ],
    },
    "route": {
        "table": "route",
        "pk": "route_id",
        "label": "Routes",
        "item": "route",
        "order_by": "route_id",
        "fields": [
            {"name": "origin_airport_id", "type": "fk", "required": True, "label": "Origin", "ref": "airport"},
            {"name": "dest_airport_id", "type": "fk", "required": True, "label": "Destination", "ref": "airport"},
            {"name": "distance_km", "type": "number", "required": True, "label": "Distance (km)"},
            {"name": "std_duration_min", "type": "number", "required": True, "label": "Duration (min)"},
        ],
    },
    "aircraft": {
        "table": "aircraft",
        "pk": "aircraft_id",
        "label": "Aircraft",
        "item": "aircraft",
        "order_by": "registration",
        "fields": [
            {"name": "registration", "type": "text", "required": True, "label": "Registration"},
            {"name": "type_id", "type": "fk", "required": True, "label": "Type", "ref": "aircraft_type"},
            {"name": "base_airport_id", "type": "fk", "required": True, "label": "Base Airport", "ref": "airport"},
            {
                "name": "status",
                "type": "select",
                "required": True,
                "label": "Status",
                "options": ["ACTIVE", "MAINTENANCE", "GROUNDED", "RETIRED"],
            },
        ],
    },
    "maintenance_log": {
        "table": "maintenance_log",
        "pk": "maint_id",
        "label": "Maintenance Log",
        "item": "maintenance entry",
        "order_by": "maint_start DESC",
        "fields": [
            {"name": "aircraft_id", "type": "fk", "required": True, "label": "Aircraft", "ref": "aircraft"},
            {"name": "maint_start", "type": "datetime", "required": True, "label": "Start"},
            {"name": "maint_end", "type": "datetime", "required": True, "label": "End"},
            {
                "name": "type",
                "type": "select",
                "required": True,
                "label": "Type",
                "options": [
                    "SCHEDULED", "UNSCHEDULED", "A_CHECK", "B_CHECK", "C_CHECK", "D_CHECK", "LINE_MAINTENANCE",
                ],
            },
        ],
    },
}

REF_LOOKUPS = {
    "airport": ("airport", "airport_id", "iata_code"),
    "aircraft_type": ("aircraft_type", "type_id", "model"),
    "aircraft": ("aircraft", "aircraft_id", "registration"),
    "delay_reason": ("delay_reason", "reason_id", "category"),
}


def fk_options(ref):
    table, pk, label_col = REF_LOOKUPS[ref]
    return query(f"SELECT {pk} AS id, {label_col} AS label FROM {table} ORDER BY {label_col}")


# MySQL data types -> form field types, for columns added after this config was written.
_INPUT_TYPES = {
    "int": "number", "bigint": "number", "smallint": "number", "tinyint": "number", "mediumint": "number",
    "decimal": "number", "float": "number", "double": "number",
    "date": "date", "datetime": "datetime", "timestamp": "datetime", "time": "time", "enum": "select",
}


def _q(name):
    """Backtick-quote an identifier (names come from config or information_schema)."""
    return "`" + name.replace("`", "``") + "`"


def fields(entity):
    """The configured fields that still exist, plus any column added to the table
    since (ALTER TABLE ... ADD COLUMN), read live from information_schema.
    ENUM options are read live too, so ALTER ... MODIFY ENUM shows up at once."""
    cfg = ENTITIES[entity]
    live = {
        c["name"]: c
        for c in query(
            """SELECT column_name AS name, data_type AS dtype, column_type AS ctype,
                      is_nullable AS nullable, column_default AS dflt, extra AS extra
               FROM information_schema.columns
               WHERE table_schema = DATABASE() AND table_name = %s
               ORDER BY ordinal_position""",
            (cfg["table"],),
        )
    }
    out = []
    for f in cfg["fields"]:
        if f["name"] not in live:
            continue  # column was dropped
        f = dict(f)
        if f["type"] == "select":
            f["options"] = enum_values(cfg["table"], f["name"]) or f["options"]
        out.append(f)

    known = {f["name"] for f in cfg["fields"]} | {cfg["pk"], "created_at", "updated_at"}
    for name, c in live.items():
        generated = "GENERATED" in c["extra"].upper() and "DEFAULT_GENERATED" not in c["extra"].upper()
        if name in known or generated:
            continue
        ftype = _INPUT_TYPES.get(c["dtype"].lower(), "text")
        out.append({
            "name": name,
            "type": ftype,
            "required": c["nullable"] == "NO" and c["dflt"] is None and "auto_increment" not in c["extra"],
            "label": name.replace("_", " ").capitalize(),
            "options": enum_values(cfg["table"], name) if ftype == "select" else None,
            "added": True,
        })
    return out


def _values(flds, data):
    values = []
    for f in flds:
        v = data.get(f["name"]) or None
        if v and f["type"] == "datetime":
            v = v.replace("T", " ")
        values.append(v)
    return values


def _select(cfg, flds):
    return ", ".join(_q(n) for n in [cfg["pk"]] + [f["name"] for f in flds])


def list_rows(entity, flds):
    cfg = ENTITIES[entity]
    return query(f"SELECT {_select(cfg, flds)} FROM {_q(cfg['table'])} ORDER BY {cfg['order_by']}")


def get_row(entity, row_id, flds):
    cfg = ENTITIES[entity]
    rows = query(f"SELECT {_select(cfg, flds)} FROM {_q(cfg['table'])} WHERE {_q(cfg['pk'])}=%s", (row_id,))
    return rows[0] if rows else None


def create_row(entity, data, flds):
    cfg = ENTITIES[entity]
    placeholders = ", ".join(["%s"] * len(flds))
    return execute(
        f"INSERT INTO {_q(cfg['table'])} ({', '.join(_q(f['name']) for f in flds)}) VALUES ({placeholders})",
        _values(flds, data),
    )


def update_row(entity, row_id, data, flds):
    cfg = ENTITIES[entity]
    set_clause = ", ".join(f"{_q(f['name'])}=%s" for f in flds)
    execute(
        f"UPDATE {_q(cfg['table'])} SET {set_clause} WHERE {_q(cfg['pk'])}=%s",
        _values(flds, data) + [row_id],
    )


def delete_row(entity, row_id):
    cfg = ENTITIES[entity]
    execute(f"DELETE FROM {cfg['table']} WHERE {cfg['pk']}=%s", (row_id,))
````

### A.37 `src/services/airports.py`

````python
from src.db import query


def list_airports():
    return query(
        """SELECT a.*, (SELECT COUNT(*) FROM gate g WHERE g.airport_id = a.airport_id) AS gates,
                  (SELECT COUNT(*) FROM v_flight_times ft
                    WHERE ft.origin_airport_id = a.airport_id AND DATE(ft.std) = CURDATE()) AS departures_today,
                  (SELECT COUNT(*) FROM v_flight_times ft
                    WHERE ft.origin_airport_id = a.airport_id AND ft.display_status = 'DELAYED') AS delayed_departures
           FROM airport a ORDER BY a.airport_id"""
    )


def get_airport(airport_id):
    rows = query("SELECT * FROM airport WHERE airport_id=%s", (airport_id,))
    return rows[0] if rows else None


def departures(airport_id, date):
    return query(
        """SELECT * FROM v_flight_times WHERE origin_airport_id=%s AND DATE(std)=%s ORDER BY std""",
        (airport_id, date),
    )


def arrivals(airport_id, date):
    return query(
        """SELECT * FROM v_flight_times WHERE dest_airport_id=%s AND DATE(sta)=%s ORDER BY sta""",
        (airport_id, date),
    )


def board_dates():
    return [r["d"] for r in query("SELECT DISTINCT DATE(sched_departure) AS d FROM flight ORDER BY d")]
````

### A.38 `src/services/bookings.py`

````python
from src.db import query, execute, call_proc_with_out


def list_bookings(status=None):
    sql = """SELECT b.booking_id, b.pnr, b.status, b.booking_date, p.name AS passenger_name
              FROM booking b JOIN passenger p ON p.passenger_id = b.passenger_id WHERE 1=1"""
    params = []
    if status:
        sql += " AND b.status = %s"
        params.append(status)
    sql += " ORDER BY b.booking_date DESC"
    return query(sql, params)


def get_booking(booking_id):
    rows = query(
        """SELECT b.*, p.name AS passenger_name
           FROM booking b JOIN passenger p ON p.passenger_id = b.passenger_id
           WHERE b.booking_id=%s""",
        (booking_id,),
    )
    return rows[0] if rows else None


def get_booking_id_by_pnr(pnr):
    rows = query("SELECT booking_id FROM booking WHERE pnr=%s", (pnr,))
    return rows[0]["booking_id"] if rows else None


def tickets_for_booking(booking_id):
    return query(
        """SELECT t.ticket_id, t.flight_id, f.flight_number, t.seat_no, t.fare, t.class,
                  t.checked_in_at, t.boarded_at
           FROM ticket t JOIN flight f ON f.flight_id = t.flight_id
           WHERE t.booking_id=%s""",
        (booking_id,),
    )


def book_ticket(passenger_id, flight_id, seat_no, ticket_class, fare):
    """Creates a new booking + its first ticket atomically via book_ticket()
    (05_procedures.sql). Returns the new booking_id."""
    result = call_proc_with_out(
        "book_ticket", (passenger_id, flight_id, seat_no, ticket_class, fare, "")
    )
    pnr = result[5]
    return get_booking_id_by_pnr(pnr)


def add_ticket(booking_id, flight_id, seat_no, ticket_class, fare):
    execute(
        """INSERT INTO ticket (booking_id, flight_id, seat_no, fare, class)
           VALUES (%s,%s,%s,%s,%s)""",
        (booking_id, flight_id, seat_no, fare, ticket_class),
    )


def cancel_booking(booking_id):
    execute(
        "UPDATE booking SET status='CANCELLED', cancelled_at=NOW() WHERE booking_id=%s",
        (booking_id,),
    )


def check_in_ticket(ticket_id):
    execute("UPDATE ticket SET checked_in_at = NOW() WHERE ticket_id=%s", (ticket_id,))
````

### A.39 `src/services/cascade.py`

````python
from src.db import query, call_proc


def analyse_cascade(flight_id):
    result_sets = call_proc("analyse_cascade", (flight_id,))
    return result_sets[0] if result_sets else []


def affected_passengers(flight_id):
    return query(
        """WITH RECURSIVE cascade_tree AS (
             SELECT flight_id FROM flight WHERE flight_id = %s
             UNION ALL
             SELECT f.flight_id FROM flight f
             JOIN cascade_tree ct ON f.parent_flight_id = ct.flight_id
           )
           SELECT DISTINCT p.passenger_id, p.name, p.email, t.flight_id, t.seat_no, t.class
           FROM cascade_tree ct
           JOIN ticket t ON t.flight_id = ct.flight_id
           JOIN booking b ON b.booking_id = t.booking_id AND b.status = 'CONFIRMED'
           JOIN passenger p ON p.passenger_id = b.passenger_id
           ORDER BY t.flight_id, p.name""",
        (flight_id,),
    )
````

### A.40 `src/services/crew.py`

````python
from src.db import query, execute, call_proc


def list_crew(role=None):
    sql = """SELECT c.crew_id, c.name, c.role, c.hire_date, c.terminated_at, a.iata_code AS base
              FROM crew c JOIN airport a ON a.airport_id = c.base_airport_id WHERE 1=1"""
    params = []
    if role:
        sql += " AND c.role = %s"
        params.append(role)
    sql += " ORDER BY c.name"
    return query(sql, params)


def get_crew(crew_id):
    rows = query(
        """SELECT c.*, a.iata_code AS base
           FROM crew c JOIN airport a ON a.airport_id = c.base_airport_id
           WHERE c.crew_id=%s""",
        (crew_id,),
    )
    return rows[0] if rows else None


def create_crew(data):
    return execute(
        "INSERT INTO crew (name, role, base_airport_id, hire_date) VALUES (%s,%s,%s,%s)",
        (data["name"], data["role"], data["base_airport_id"], data["hire_date"]),
    )


def update_crew(crew_id, data):
    execute(
        """UPDATE crew SET name=%s, role=%s, base_airport_id=%s, hire_date=%s, terminated_at=%s
           WHERE crew_id=%s""",
        (
            data["name"],
            data["role"],
            data["base_airport_id"],
            data["hire_date"],
            data.get("terminated_at") and data["terminated_at"].replace("T", " ") or None,
            crew_id,
        ),
    )


def delete_crew(crew_id):
    execute("DELETE FROM crew WHERE crew_id=%s", (crew_id,))


def certifications(crew_id):
    return query(
        """SELECT cc.type_id, at.model, at.manufacturer, cc.certified_date, cc.expiry_date
           FROM crew_certification cc
           JOIN aircraft_type at ON at.type_id = cc.type_id
           WHERE cc.crew_id=%s ORDER BY at.model""",
        (crew_id,),
    )


def add_certification(crew_id, type_id, certified_date, expiry_date):
    execute(
        """INSERT INTO crew_certification (crew_id, type_id, certified_date, expiry_date)
           VALUES (%s,%s,%s,%s)""",
        (crew_id, type_id, certified_date, expiry_date),
    )


def remove_certification(crew_id, type_id):
    execute(
        "DELETE FROM crew_certification WHERE crew_id=%s AND type_id=%s",
        (crew_id, type_id),
    )


def duty_status():
    return query(
        """SELECT c.crew_id, c.name, c.role, dl.duty_date, dl.hours_on_duty, dl.hours_flown,
                  ROUND(11 - dl.hours_on_duty, 2) AS hours_remaining
           FROM crew c JOIN duty_log dl ON dl.crew_id = c.crew_id
           WHERE dl.duty_date = CURDATE() AND dl.hours_on_duty >= 8
           ORDER BY dl.hours_on_duty DESC"""
    )


def replacement_crew(flight_id):
    result_sets = call_proc("find_replacement_crew", (flight_id,))
    return result_sets[0] if result_sets else []
````

### A.41 `src/services/dashboard.py`

````python
from src.db import query


def summary():
    return {
        "flights_today": query(
            "SELECT COUNT(*) AS n FROM flight WHERE DATE(sched_departure) = CURDATE()"
        )[0]["n"],
        "delayed_now": query(
            "SELECT COUNT(*) AS n FROM flight "
            "WHERE delay_minutes > 0 AND status NOT IN ('ARRIVED', 'CANCELLED')"
        )[0]["n"],
        "active_aircraft": query(
            "SELECT COUNT(*) AS n FROM aircraft WHERE status = 'ACTIVE'"
        )[0]["n"],
        "crew_on_duty": query(
            "SELECT COUNT(DISTINCT crew_id) AS n FROM duty_log WHERE duty_date = CURDATE()"
        )[0]["n"],
        "flights_this_week": query("SELECT COUNT(*) AS n FROM flight")[0]["n"],
        "knock_on_flights": query("SELECT COUNT(DISTINCT flight_id) AS n FROM delay_impact")[0]["n"],
        "confirmed_bookings": query(
            "SELECT COUNT(*) AS n FROM booking WHERE status IN ('CONFIRMED', 'CHECKED_IN')"
        )[0]["n"],
    }


def recent_delays(limit=10):
    return query(
        """SELECT fd.delay_id, f.flight_number, dr.category, fd.minutes, fd.recorded_at,
                  (SELECT COUNT(*) FROM delay_impact di WHERE di.delay_id = fd.delay_id) AS knock_on
           FROM flight_delay fd
           JOIN flight f ON f.flight_id = fd.flight_id
           JOIN delay_code dc ON dc.code_id = fd.code_id
           JOIN delay_reason dr ON dr.reason_id = dc.reason_id
           ORDER BY fd.recorded_at DESC
           LIMIT %s""",
        (limit,),
    )


def network_routes():
    """Undirected airport pairs with at least one scheduled flight, for the
    dashboard's network constellation."""
    return query(
        """SELECT DISTINCT LEAST(r.origin_airport_id, r.dest_airport_id) AS a,
                           GREATEST(r.origin_airport_id, r.dest_airport_id) AS b
           FROM route r WHERE EXISTS (SELECT 1 FROM flight f WHERE f.route_id = r.route_id)"""
    )
````

### A.42 `src/services/delays.py`

````python
"""Delay notices and their organisation-wide impact. Filing a notice runs the
cascade engine, simulate_delay() in 05_procedures.sql."""

from src.db import query, execute, call_proc, call_proc_with_out

NOTICE_FIELDS = (
    "minutes", "code_id", "sub_reason", "phase", "ops_status", "new_gate_id",
    "new_boarding_time", "pax_deboarded", "swap_aircraft_id", "announcement",
    "meal_voucher", "compensation_eligible", "rebooking_offered", "reported_by", "remarks",
)

# Non-timing fields that can be edited after filing. Changing minutes would
# leave the recorded cascade inconsistent, so that means filing another notice.
EDITABLE_FIELDS = (
    "sub_reason", "announcement", "pax_deboarded", "meal_voucher", "compensation_eligible",
    "rebooking_offered", "reported_by", "remarks",
)


def file_delay(flight_id, notice):
    """Files the notice and cascades it. Returns the new delay_id."""
    args = (flight_id,) + tuple(notice[f] for f in NOTICE_FIELDS) + (0,)
    return call_proc_with_out("simulate_delay", args)[-1]


def get_delay(delay_id):
    rows = query(
        """SELECT fd.*, dr.category, dc.iata_code, dc.description AS code_description,
                  ft.flight_number, ft.origin, ft.dest, ft.std, ft.etd, ft.eta, ft.display_status,
                  ng.gate_code AS new_gate_code, sa.registration AS swap_registration
           FROM flight_delay fd
           JOIN delay_code dc ON dc.code_id = fd.code_id
           JOIN delay_reason dr ON dr.reason_id = dc.reason_id
           JOIN v_flight_times ft ON ft.flight_id = fd.flight_id
           LEFT JOIN gate ng ON ng.gate_id = fd.new_gate_id
           LEFT JOIN aircraft sa ON sa.aircraft_id = fd.swap_aircraft_id
           WHERE fd.delay_id = %s""",
        (delay_id,),
    )
    return rows[0] if rows else None


def list_delays(open_only=False):
    sql = """SELECT fd.delay_id, fd.flight_id, ft.flight_number, ft.origin, ft.dest, ft.std,
                    dr.category, dc.iata_code, fd.minutes, fd.ops_status, fd.reported_by,
                    fd.recorded_at, fd.resolved_at,
                    (SELECT COUNT(*) FROM delay_impact di WHERE di.delay_id = fd.delay_id) AS knock_on_flights,
                    (SELECT COALESCE(SUM(di.minutes_added), 0) FROM delay_impact di
                      WHERE di.delay_id = fd.delay_id) AS knock_on_minutes
             FROM flight_delay fd
             JOIN v_flight_times ft ON ft.flight_id = fd.flight_id
             JOIN delay_code dc ON dc.code_id = fd.code_id
             JOIN delay_reason dr ON dr.reason_id = dc.reason_id"""
    if open_only:
        sql += " WHERE fd.resolved_at IS NULL"
    return query(sql + " ORDER BY fd.recorded_at DESC, fd.delay_id DESC")


def impacts(delay_id):
    return query(
        """SELECT di.impact_id, di.link, di.minutes_added, di.old_etd, di.new_etd, di.pass_no,
                  ft.flight_id, ft.flight_number, ft.origin, ft.dest, ft.registration,
                  ft.std, ft.etd, ft.delay_minutes, ft.gate_code,
                  cf.flight_id AS cause_flight_id, cf.flight_number AS cause_flight
           FROM delay_impact di
           JOIN v_flight_times ft ON ft.flight_id = di.flight_id
           LEFT JOIN flight cf ON cf.flight_id = di.cause_flight_id
           WHERE di.delay_id = %s
           ORDER BY di.pass_no, di.new_etd""",
        (delay_id,),
    )


def _in(ids):
    return ", ".join(["%s"] * len(ids))


def affected_summary(flight_ids):
    """Operational fallout for a set of flights, read from the flag views."""
    ids = list(flight_ids)
    if not ids:
        return {"missed": [], "duty": [], "curfew": [], "passengers": 0, "aircraft": 0, "airports": 0}
    return {
        "missed": query(
            f"""SELECT * FROM v_missed_connections
                WHERE in_flight_id IN ({_in(ids)}) OR out_flight_id IN ({_in(ids)})
                ORDER BY in_eta""",
            ids + ids,
        ),
        "duty": query(
            f"""SELECT DISTINCT b.* FROM v_duty_breaches b
                JOIN crew_assignment ca ON ca.crew_id = b.crew_id AND ca.unassigned_at IS NULL
                JOIN flight f ON f.flight_id = ca.flight_id AND DATE(f.sched_departure) = b.duty_date
                WHERE ca.flight_id IN ({_in(ids)})
                ORDER BY b.duty_hours DESC""",
            ids,
        ),
        "curfew": query(f"SELECT * FROM v_curfew_risk WHERE flight_id IN ({_in(ids)})", ids),
        "passengers": query(
            f"""SELECT COUNT(DISTINCT b.passenger_id) AS n FROM ticket t
                JOIN booking b ON b.booking_id = t.booking_id AND b.status IN ('CONFIRMED', 'CHECKED_IN')
                WHERE t.flight_id IN ({_in(ids)})""",
            ids,
        )[0]["n"],
        "aircraft": query(
            f"SELECT COUNT(DISTINCT aircraft_id) AS n FROM flight WHERE flight_id IN ({_in(ids)})", ids
        )[0]["n"],
        "airports": query(
            f"""SELECT COUNT(DISTINCT r.origin_airport_id) AS n FROM flight f
                JOIN route r ON r.route_id = f.route_id WHERE f.flight_id IN ({_in(ids)})""",
            ids,
        )[0]["n"],
    }


def update_notice(delay_id, notice):
    execute(
        f"UPDATE flight_delay SET {', '.join(f'{f}=%s' for f in EDITABLE_FIELDS)} WHERE delay_id=%s",
        tuple(notice[f] for f in EDITABLE_FIELDS) + (delay_id,),
    )


def resolve(delay_id):
    execute("UPDATE flight_delay SET resolved_at = NOW() WHERE delay_id=%s AND resolved_at IS NULL", (delay_id,))


def reset_all():
    call_proc("reset_all_delays")


def network_flags():
    return {
        "missed": query("SELECT COUNT(*) AS n FROM v_missed_connections")[0]["n"],
        "duty": query("SELECT COUNT(*) AS n FROM v_duty_breaches")[0]["n"],
        "curfew": query("SELECT COUNT(*) AS n FROM v_curfew_risk")[0]["n"],
    }
````

### A.43 `src/services/flights.py`

````python
from src.db import query, execute

# v_flight_times (06_views.sql) derives ETD/ETA/display status from delay_minutes.
LIST_SELECT = """
    SELECT ft.*, ft.std AS sched_departure, ft.sta AS sched_arrival
    FROM v_flight_times ft
"""


def _dt(value):
    """datetime-local inputs submit 'YYYY-MM-DDTHH:MM'; MySQL wants a space."""
    if not value:
        return None
    return value.replace("T", " ")


def list_flights(status=None, date=None, q=None):
    sql = LIST_SELECT + " WHERE 1=1"
    params = []
    if status == "DELAYED":
        sql += " AND ft.display_status = 'DELAYED'"
    elif status:
        sql += " AND ft.status = %s"
        params.append(status)
    if date:
        sql += " AND DATE(ft.std) = %s"
        params.append(date)
    if q:
        sql += " AND (ft.flight_number LIKE %s OR ft.origin = %s OR ft.dest = %s OR ft.registration LIKE %s)"
        params += [f"%{q}%", q.upper(), q.upper(), f"%{q}%"]
    sql += " ORDER BY ft.std"
    return query(sql, params)


def get_flight(flight_id):
    rows = query(
        """SELECT ft.*, ft.std AS sched_departure, ft.sta AS sched_arrival, f.gate_close,
                  og.gate_code AS gate_label, o.city AS origin_city, d.city AS dest_city
           FROM v_flight_times ft
           JOIN flight f ON f.flight_id = ft.flight_id
           JOIN airport o ON o.airport_id = ft.origin_airport_id
           JOIN airport d ON d.airport_id = ft.dest_airport_id
           LEFT JOIN gate og ON og.gate_id = ft.gate_id
           WHERE ft.flight_id = %s""",
        (flight_id,),
    )
    return rows[0] if rows else None


def crew_for_flight(flight_id):
    return query(
        """SELECT ca.crew_id, c.name, ca.role, ca.assigned_at
           FROM crew_assignment ca
           JOIN crew c ON c.crew_id = ca.crew_id
           WHERE ca.flight_id = %s AND ca.unassigned_at IS NULL""",
        (flight_id,),
    )


def delays_for_flight(flight_id):
    """Delay notices filed directly on this flight."""
    return query(
        """SELECT fd.delay_id, dr.category, dc.iata_code, dc.description, fd.sub_reason,
                  fd.minutes, fd.ops_status, fd.reported_by, fd.recorded_at, fd.resolved_at
           FROM flight_delay fd
           JOIN delay_code dc ON dc.code_id = fd.code_id
           JOIN delay_reason dr ON dr.reason_id = dc.reason_id
           WHERE fd.flight_id = %s
           ORDER BY fd.recorded_at""",
        (flight_id,),
    )


def knock_on_for_flight(flight_id):
    """Delay this flight received from other flights' notices via the cascade."""
    return query(
        """SELECT di.delay_id, di.link, di.minutes_added, di.old_etd, di.new_etd,
                  cf.flight_id AS cause_flight_id, cf.flight_number AS cause_flight,
                  src.flight_number AS source_flight
           FROM delay_impact di
           JOIN flight_delay fd ON fd.delay_id = di.delay_id
           JOIN flight src ON src.flight_id = fd.flight_id
           LEFT JOIN flight cf ON cf.flight_id = di.cause_flight_id
           WHERE di.flight_id = %s
           ORDER BY di.impact_id""",
        (flight_id,),
    )


def gate_matches_route(gate_id, route_id):
    if not gate_id:
        return True
    return bool(query(
        """SELECT 1 FROM gate g JOIN route r ON r.origin_airport_id = g.airport_id
           WHERE g.gate_id = %s AND r.route_id = %s""",
        (gate_id, route_id),
    ))


def create_flight(data):
    return execute(
        """INSERT INTO flight
           (flight_number, route_id, aircraft_id, sched_departure, sched_arrival,
            boarding_start, gate_close, status, gate_id, remarks)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (
            data["flight_number"],
            data["route_id"],
            data["aircraft_id"],
            _dt(data["sched_departure"]),
            _dt(data["sched_arrival"]),
            _dt(data.get("boarding_start")),
            _dt(data.get("gate_close")),
            data.get("status") or "SCHEDULED",
            data.get("gate_id") or None,
            data.get("remarks") or None,
        ),
    )


def update_flight(flight_id, data):
    execute(
        """UPDATE flight SET
             flight_number=%s, route_id=%s, aircraft_id=%s,
             sched_departure=%s, sched_arrival=%s,
             boarding_start=%s, gate_close=%s,
             actual_departure=%s, actual_arrival=%s, status=%s,
             gate_id=%s, remarks=%s
           WHERE flight_id=%s""",
        (
            data["flight_number"],
            data["route_id"],
            data["aircraft_id"],
            _dt(data["sched_departure"]),
            _dt(data["sched_arrival"]),
            _dt(data.get("boarding_start")),
            _dt(data.get("gate_close")),
            _dt(data.get("actual_departure")),
            _dt(data.get("actual_arrival")),
            data.get("status") or "SCHEDULED",
            data.get("gate_id") or None,
            data.get("remarks") or None,
            flight_id,
        ),
    )


def delete_flight(flight_id):
    execute("DELETE FROM flight WHERE flight_id=%s", (flight_id,))


def assign_crew(flight_id, crew_id, role):
    execute(
        # Unassign is a soft delete, so re-assigning reactivates the existing row.
        """INSERT INTO crew_assignment (flight_id, crew_id, role) VALUES (%s, %s, %s)
           ON DUPLICATE KEY UPDATE role = VALUES(role), assigned_at = NOW(), unassigned_at = NULL""",
        (flight_id, crew_id, role),
    )


def unassign_crew(flight_id, crew_id):
    execute(
        "UPDATE crew_assignment SET unassigned_at = NOW() WHERE flight_id=%s AND crew_id=%s",
        (flight_id, crew_id),
    )
````

### A.44 `src/services/lookups.py`

````python
"""Shared dropdown lookups. Every function returns rows shaped {id, label}."""

import re

from src.db import query


def airports():
    return query(
        "SELECT airport_id AS id, CONCAT(iata_code, ' — ', city) AS label "
        "FROM airport ORDER BY iata_code"
    )


def aircraft_types():
    return query(
        "SELECT type_id AS id, CONCAT(manufacturer, ' ', model) AS label "
        "FROM aircraft_type ORDER BY manufacturer, model"
    )


def aircraft():
    return query(
        "SELECT aircraft_id AS id, registration AS label "
        "FROM aircraft WHERE status <> 'RETIRED' ORDER BY registration"
    )


def routes():
    return query(
        """SELECT r.route_id AS id, CONCAT(o.iata_code, ' → ', d.iata_code) AS label
           FROM route r
           JOIN airport o ON o.airport_id = r.origin_airport_id
           JOIN airport d ON d.airport_id = r.dest_airport_id
           WHERE r.deactivated_at IS NULL
           ORDER BY o.iata_code, d.iata_code"""
    )



def crew():
    return query(
        "SELECT crew_id AS id, CONCAT(name, ', ', LOWER(REPLACE(role, '_', ' '))) AS label "
        "FROM crew WHERE terminated_at IS NULL ORDER BY name"
    )


def gates(airport_id=None):
    sql = """SELECT g.gate_id AS id, CONCAT(a.iata_code, ' ', g.gate_code, ' (', g.terminal, ')') AS label
             FROM gate g JOIN airport a ON a.airport_id = g.airport_id"""
    params = ()
    if airport_id:
        sql += " WHERE g.airport_id = %s"
        params = (airport_id,)
    return query(sql + " ORDER BY a.iata_code, g.terminal, g.gate_id", params)


def delay_codes():
    """IATA codes with their category, ordered for a grouped <select>."""
    return query(
        """SELECT dc.code_id AS id, dc.iata_code, dc.description, dr.category
           FROM delay_code dc JOIN delay_reason dr ON dr.reason_id = dc.reason_id
           ORDER BY dr.category, dc.iata_code"""
    )


def enum_values(table, column):
    """The column's ENUM members, read live from information_schema, so an
    ALTER TABLE ... MODIFY ... ENUM(...) shows up in every dropdown at once."""
    rows = query(
        """SELECT column_type AS ctype FROM information_schema.columns
           WHERE table_schema = DATABASE() AND table_name = %s AND column_name = %s""",
        (table, column),
    )
    if not rows or not rows[0]["ctype"].lower().startswith("enum("):
        return []
    return [v.replace("''", "'") for v in re.findall(r"'((?:[^']|'')*)'", rows[0]["ctype"])]
````

### A.45 `src/services/passengers.py`

````python
from src.db import query, execute


def list_passengers(search=None):
    sql = "SELECT passenger_id, name, passport_no, email, phone, date_of_birth FROM passenger WHERE 1=1"
    params = []
    if search:
        sql += " AND name LIKE %s"
        params.append(f"%{search}%")
    sql += " ORDER BY name"
    return query(sql, params)


def get_passenger(passenger_id):
    rows = query("SELECT * FROM passenger WHERE passenger_id=%s", (passenger_id,))
    return rows[0] if rows else None


def create_passenger(data):
    return execute(
        """INSERT INTO passenger (name, passport_no, email, phone, date_of_birth)
           VALUES (%s,%s,%s,%s,%s)""",
        (
            data["name"],
            data.get("passport_no") or None,
            data.get("email") or None,
            data.get("phone") or None,
            data["date_of_birth"],
        ),
    )


def update_passenger(passenger_id, data):
    execute(
        """UPDATE passenger SET name=%s, passport_no=%s, email=%s, phone=%s, date_of_birth=%s
           WHERE passenger_id=%s""",
        (
            data["name"],
            data.get("passport_no") or None,
            data.get("email") or None,
            data.get("phone") or None,
            data["date_of_birth"],
            passenger_id,
        ),
    )


def delete_passenger(passenger_id):
    execute("DELETE FROM passenger WHERE passenger_id=%s", (passenger_id,))


def bookings_for_passenger(passenger_id):
    return query(
        "SELECT booking_id, pnr, booking_date, status FROM booking "
        "WHERE passenger_id=%s ORDER BY booking_date DESC",
        (passenger_id,),
    )
````

### A.46 `src/services/reports.py`

````python
from src.db import query
from src.services.crew import duty_status  # noqa: F401 (re-exported for reports.duty_status)


def ontime_performance():
    return query(
        """SELECT DATE(sched_departure) AS flight_date, COUNT(*) AS total_flights,
                  SUM(CASE WHEN delay_minutes <= 15 THEN 1 ELSE 0 END) AS on_time_flights,
                  ROUND(100 * SUM(CASE WHEN delay_minutes <= 15 THEN 1 ELSE 0 END) / COUNT(*), 1) AS on_time_pct
           FROM flight WHERE status <> 'CANCELLED'
           GROUP BY DATE(sched_departure) ORDER BY flight_date"""
    )


def top_delay_causes():
    return query(
        """SELECT dr.category, COUNT(*) AS delay_count, SUM(fd.minutes) AS total_minutes,
                  ROUND(AVG(fd.minutes), 1) AS avg_minutes
           FROM flight_delay fd
           JOIN delay_code dc ON dc.code_id = fd.code_id
           JOIN delay_reason dr ON dr.reason_id = dc.reason_id
           GROUP BY dr.category ORDER BY delay_count DESC"""
    )


def load_factor():
    return query(
        """SELECT f.flight_id, f.flight_number, f.sched_departure, at.seat_capacity,
                  COUNT(t.ticket_id) AS tickets_sold,
                  ROUND(100 * COUNT(t.ticket_id) / at.seat_capacity, 1) AS load_factor_pct
           FROM flight f
           JOIN aircraft a ON a.aircraft_id = f.aircraft_id
           JOIN aircraft_type at ON at.type_id = a.type_id
           LEFT JOIN (
             SELECT t.ticket_id, t.flight_id FROM ticket t
             JOIN booking b ON b.booking_id = t.booking_id WHERE b.status <> 'CANCELLED'
           ) t ON t.flight_id = f.flight_id
           GROUP BY f.flight_id, f.flight_number, f.sched_departure, at.seat_capacity
           ORDER BY f.sched_departure"""
    )


def aircraft_utilisation():
    return query(
        """SELECT a.aircraft_id, a.registration, at.model, COUNT(f.flight_id) AS flights_operated,
                  ROUND(SUM(TIMESTAMPDIFF(MINUTE, f.sched_departure, f.sched_arrival)) / 60, 1) AS scheduled_flight_hours,
                  ROUND(SUM(f.delay_minutes) / 60, 1) AS total_delay_hours
           FROM aircraft a JOIN aircraft_type at ON at.type_id = a.type_id
           LEFT JOIN flight f ON f.aircraft_id = a.aircraft_id AND f.status <> 'CANCELLED'
           GROUP BY a.aircraft_id, a.registration, at.model
           ORDER BY flights_operated DESC"""
    )
````

### A.47 `src/services/schema_info.py`

````python
from src.db import query
from src.config import Settings


def _q(name):
    return "`" + name.replace("`", "``") + "`"


def tables():
    """Base tables with EXACT row counts. information_schema.tables.table_rows is
    an InnoDB estimate that MySQL caches (information_schema_stats_expiry), so it
    goes stale right after someone inserts rows by hand."""
    rows = query(
        """SELECT table_name AS table_name, create_time AS create_time
           FROM information_schema.tables
           WHERE table_schema = %s AND table_type = 'BASE TABLE'
           ORDER BY table_name""",
        (Settings.DB_NAME,),
    )
    for r in rows:
        r["table_rows"] = query(f"SELECT COUNT(*) AS n FROM {_q(r['table_name'])}")[0]["n"]
    return rows


def views():
    return query(
        """SELECT table_name AS table_name FROM information_schema.views
           WHERE table_schema = %s ORDER BY table_name""",
        (Settings.DB_NAME,),
    )


def columns(table_name):
    return query(
        """SELECT column_name AS column_name, column_type AS column_type,
                  is_nullable AS is_nullable, column_key AS column_key,
                  column_default AS column_default, extra AS extra
           FROM information_schema.columns
           WHERE table_schema = %s AND table_name = %s
           ORDER BY ordinal_position""",
        (Settings.DB_NAME, table_name),
    )


def foreign_keys(table_name):
    return query(
        """SELECT column_name AS column_name,
                  referenced_table_name AS referenced_table_name,
                  referenced_column_name AS referenced_column_name
           FROM information_schema.key_column_usage
           WHERE table_schema = %s AND table_name = %s AND referenced_table_name IS NOT NULL""",
        (Settings.DB_NAME, table_name),
    )


def record(table, pk, row_id):
    """Every column of one row, exactly as stored. Table and key names are
    hard-coded by the calling route, never user input."""
    rows = query(f"SELECT * FROM {_q(table)} WHERE {_q(pk)} = %s", (row_id,))
    return rows[0] if rows else None


def rows_page(table, page, per_page=50):
    """One page of SELECT * from a table or view, with its live column list.
    The name has already been checked against information_schema by the route."""
    total = query(f"SELECT COUNT(*) AS n FROM {_q(table)}")[0]["n"]
    rows = query(f"SELECT * FROM {_q(table)} LIMIT %s OFFSET %s", (per_page, (page - 1) * per_page))
    cols = [c["column_name"] for c in columns(table)]
    return cols, rows, total
````

### A.48 `tests/test_cascade.py`

````python
"""Run against a freshly seeded DB:
    bash scripts/setup_db.sh && python tests/test_cascade.py
Checks the organisation-wide cascade engine (simulate_delay) end to end."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db import query, call_proc
from src.services import delays

call_proc("reset_all_delays")

# 1. With no delays filed, the seeded schedule satisfies every cascade rule and
#    raises no flags -- so flights only ever move because of a filed delay.
call_proc("compute_cascade_candidates")
violations = query(
    """SELECT c.link, COUNT(*) AS n FROM cascade_candidate c JOIN flight f USING (flight_id)
       WHERE c.required_delay > f.delay_minutes GROUP BY c.link"""
)
assert not violations, f"schedule breaks cascade rules at zero delay: {violations}"
for view in ("v_missed_connections", "v_duty_breaches", "v_curfew_risk"):
    assert query(f"SELECT COUNT(*) AS n FROM {view}")[0]["n"] == 0, f"{view} not empty at zero delay"

# 2. Delay a hub-bound leg whose crew continue on another aircraft and which
#    carries connecting passengers: the delay must reach the same aircraft's next
#    leg, a different aircraft via crew, and break at least one connection.
flight = query(
    """SELECT f.flight_id, f.aircraft_id
       FROM flight f
       WHERE f.status = 'SCHEDULED' AND DATE(f.sched_departure) = CURDATE() + INTERVAL 1 DAY
         AND EXISTS (SELECT 1 FROM crew_assignment ca
                     JOIN crew_assignment ca2 ON ca2.crew_id = ca.crew_id
                     JOIN flight f2 ON f2.flight_id = ca2.flight_id
                     WHERE ca.flight_id = f.flight_id AND f2.aircraft_id <> f.aircraft_id
                       AND f2.sched_departure > f.sched_departure
                       AND DATE(f2.sched_departure) = DATE(f.sched_departure))
         AND EXISTS (SELECT 1 FROM ticket t JOIN ticket t2 ON t2.booking_id = t.booking_id
                     AND t2.flight_id <> t.flight_id WHERE t.flight_id = f.flight_id)
       ORDER BY f.sched_departure LIMIT 1"""
)[0]
code_id = query("SELECT code_id FROM delay_code WHERE iata_code = '41'")[0]["code_id"]
notice = {f: None for f in delays.NOTICE_FIELDS}
notice.update(minutes=180, code_id=code_id, phase="AT_GATE", ops_status="DELAYED", reported_by="test",
              pax_deboarded=False, meal_voucher=True, compensation_eligible=True, rebooking_offered=False)
delay_id = delays.file_delay(flight["flight_id"], notice)

impacts = query(
    """SELECT di.link, di.flight_id, di.minutes_added, f.aircraft_id
       FROM delay_impact di JOIN flight f USING (flight_id) WHERE di.delay_id = %s""",
    (delay_id,),
)
assert any(i["link"] == "AIRCRAFT" and i["aircraft_id"] == flight["aircraft_id"] for i in impacts), impacts
assert any(i["link"] == "CREW" and i["aircraft_id"] != flight["aircraft_id"] for i in impacts), impacts
affected = [flight["flight_id"]] + [i["flight_id"] for i in impacts]
assert delays.affected_summary(affected)["missed"], "expected at least one missed connection"

# 3. Every flight's delay is exactly what was filed on it plus its knock-on.
mismatched = query(
    """SELECT f.flight_id FROM flight f
       LEFT JOIN (SELECT flight_id, SUM(minutes) AS m FROM flight_delay GROUP BY flight_id) d USING (flight_id)
       LEFT JOIN (SELECT flight_id, SUM(minutes_added) AS m FROM delay_impact GROUP BY flight_id) k USING (flight_id)
       WHERE f.delay_minutes <> COALESCE(d.m, 0) + COALESCE(k.m, 0)"""
)
assert not mismatched, mismatched

# 4. After the cascade settles, no rule is left violated.
call_proc("compute_cascade_candidates")
assert not query(
    """SELECT 1 FROM cascade_candidate c JOIN flight f USING (flight_id)
       WHERE c.required_delay > f.delay_minutes LIMIT 1"""
), "cascade stopped before every rule was satisfied"

# 5. Reset puts the whole network back on schedule.
call_proc("reset_all_delays")
assert query("SELECT COUNT(*) AS n FROM flight WHERE delay_minutes <> 0")[0]["n"] == 0
assert query("SELECT COUNT(*) AS n FROM delay_impact")[0]["n"] == 0

print(f"ok ({len(impacts)} knock-on flights)")
````

### A.49 `tests/test_crew_assignment.py`

````python
"""Run against a freshly seeded DB:
    bash scripts/setup_db.sh && python tests/test_crew_assignment.py
Checks that soft-unassigned crew are really treated as off the flight."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db import query, execute
from src.services import flights

flight = query(
    "SELECT flight_id, DATE(sched_departure) d FROM flight WHERE actual_arrival IS NULL ORDER BY flight_id LIMIT 1"
)[0]
f, day = flight["flight_id"], flight["d"]
# A crew member not on this flight with no duty that day, so any duty_log row would come from this flight.
crew = query(
    """SELECT c.crew_id, c.role FROM crew c
       WHERE c.terminated_at IS NULL
         AND NOT EXISTS (SELECT 1 FROM crew_assignment ca WHERE ca.crew_id = c.crew_id AND ca.flight_id = %s)
         AND NOT EXISTS (SELECT 1 FROM duty_log d WHERE d.crew_id = c.crew_id AND d.duty_date = %s)
       LIMIT 1""",
    (f, day),
)[0]

# Re-assigning after unassign must reactivate the row, not hit the composite PK.
flights.assign_crew(f, crew["crew_id"], crew["role"])
flights.unassign_crew(f, crew["crew_id"])
flights.assign_crew(f, crew["crew_id"], crew["role"])
row = query("SELECT unassigned_at FROM crew_assignment WHERE flight_id=%s AND crew_id=%s", (f, crew["crew_id"]))
assert row[0]["unassigned_at"] is None
flights.unassign_crew(f, crew["crew_id"])

# Unassigned crew must not accrue duty hours when the flight lands (trg_update_duty).
execute("UPDATE flight SET actual_departure=sched_departure, actual_arrival=sched_arrival WHERE flight_id=%s", (f,))
assert not query("SELECT 1 FROM duty_log WHERE crew_id=%s AND duty_date=%s", (crew["crew_id"], day)), "unassigned crew got duty hours"

print("ok")
````

### A.50 `tests/test_live_changes.py`

````python
"""Simulates an examiner changing tables by hand in the MySQL client, then checks
the website reflects each change. Rebuilds the database at the end.

    python tests/test_live_changes.py
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app import app  # noqa: E402

env = dict(l.strip().split("=", 1) for l in open(os.path.join(ROOT, ".env")) if "=" in l)
c = app.test_client()


def mysql(sql):
    """Run SQL in a separate mysql client session, like an examiner would."""
    subprocess.run(
        ["mysql", "-h", env["DB_HOST"], "-u", env["DB_USER"], f"-p{env['DB_PASSWORD']}", env["DB_NAME"], "-e", sql],
        check=True, stderr=subprocess.DEVNULL,
    )


def page(url, status=200):
    r = c.get(url)
    assert r.status_code == status, (url, r.status_code)
    return r.get_data(as_text=True)


checks = []


def check(name, cond):
    checks.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)


try:
    # 1. INSERT a row
    mysql("INSERT INTO passenger (name, passport_no, email, phone, date_of_birth) "
          "VALUES ('Viva Examiner', 'X9999999', 'viva@example.com', '9000000000', '1980-05-05')")
    check("inserted passenger appears in search", "Viva Examiner" in page("/passengers/?q=Viva"))
    check("schema row count is exact after INSERT", ">2,001<" in page("/schema/").replace(" ", "") or "2001" in page("/schema/"))

    # 2. UPDATE rows
    mysql("UPDATE flight SET delay_minutes = 95 WHERE flight_number = 'AI-101' AND DATE(sched_departure) = CURDATE() + INTERVAL 1 DAY")
    html = page("/flights/?q=AI-101&status=DELAYED")
    check("hand-set delay shows as DELAYED with new time", "AI-101" in html and "DELAYED" in html)
    mysql("UPDATE airport SET runway_slots_per_hour = 9, min_connect_min = 50 WHERE iata_code = 'DEL'")
    check("airport rule change shows on its board", "9 departures an hour" in page("/airports/1/board"))

    # 3. ALTER TABLE ... ADD COLUMN
    mysql("ALTER TABLE passenger ADD COLUMN nationality VARCHAR(40) DEFAULT 'Indian'")
    check("new passenger column shows on the passenger page", "nationality" in page("/passengers/1"))
    mysql("ALTER TABLE airport ADD COLUMN elevation_m INT NULL")
    check("new airport column shows in admin list", "Elevation m" in page("/admin/airport/"))
    check("new airport column is editable", 'name="elevation_m"' in page("/admin/airport/1/edit"))
    form = {"iata_code": "DEL", "icao_code": "VIDP", "city": "Delhi", "country": "India", "timezone": "Asia/Kolkata",
            "open_time": "", "close_time": "", "runway_slots_per_hour": "9", "min_connect_min": "50",
            "min_turnaround_min": "60", "elevation_m": "216"}
    c.post("/admin/airport/1/edit", data=form)
    check("value saved into the new column", ">216<" in page("/admin/airport/"))

    # 4. ALTER an ENUM
    mysql("ALTER TABLE flight MODIFY status ENUM('SCHEDULED','BOARDING','DEPARTED','ARRIVED','CANCELLED','DIVERTED','ON_HOLD') "
          "DEFAULT 'SCHEDULED' NOT NULL")
    check("new ENUM value offered in the flight form", 'value="ON_HOLD"' in page("/flights/new"))
    mysql("UPDATE flight SET status = 'ON_HOLD' WHERE flight_number = 'AI-102' AND DATE(sched_departure) = CURDATE() + INTERVAL 2 DAY")
    check("flight in the new status displays it", "ON HOLD" in page("/flights/?status=ON_HOLD"))
    mysql("ALTER TABLE crew MODIFY role ENUM('CAPTAIN','FIRST_OFFICER','CABIN_CREW','PURSER','FLIGHT_ENGINEER') NOT NULL")
    check("new crew role offered in the crew form", 'value="FLIGHT_ENGINEER"' in page("/crew/new"))

    # 5. New rows in reference tables, new views
    mysql("INSERT INTO airport (iata_code, icao_code, city, country, timezone) VALUES ('IXZ','VOPB','Port Blair','India','Asia/Kolkata')")
    check("SQL-inserted airport appears on Airports", "Port Blair" in page("/airports/"))
    check("SQL-inserted airport appears on the dashboard map data", "Port Blair" in page("/"))
    mysql("CREATE VIEW v_viva_check AS SELECT flight_number, delay_minutes FROM flight WHERE delay_minutes > 0")
    check("new view listed on Schema", "v_viva_check" in page("/schema/"))
    check("new view's rows browsable", "AI-101" in page("/schema/v_viva_check/rows"))

    # 6. DELETE
    mysql("DELETE FROM passenger WHERE passport_no = 'X9999999'")
    check("deleted passenger is gone", "Viva Examiner" not in page("/passengers/?q=Viva"))

    # 7. Renamed columns: pages reading SELECT * adapt; pages naming the column report it
    mysql("ALTER TABLE passenger RENAME COLUMN email TO email_address")
    check("renamed column shows under its new name", "email_address" in page("/passengers/1"))
    mysql("ALTER TABLE booking RENAME COLUMN pnr TO pnr_code")
    html = page("/bookings/", status=500)
    check("breaking change gives a readable error page", "database rejected" in html and "pnr" in html)
finally:
    subprocess.run(["bash", os.path.join(ROOT, "scripts/setup_db.sh")], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

failed = [n for n, ok in checks if not ok]
print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed; database rebuilt.")
sys.exit(1 if failed else 0)
````

### A.51 `scripts/build_report_context.py`

````python
"""Builds docs/REPORT_CONTEXT.md: everything needed to write the project report,
filled with figures measured from the live project.

    python scripts/build_report_context.py

It rebuilds the database several times (scripts/setup_db.sh), runs a demo
cascade and every test, and leaves the database freshly seeded. Takes 1-2 min.
The narrative lives in scripts/report_template.md; {{PLACEHOLDERS}} there are
filled in here.
"""
import datetime
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
OUT = os.path.join(ROOT, "docs", "REPORT_CONTEXT.md")
ENV = dict(l.strip().split("=", 1) for l in open(os.path.join(ROOT, ".env")) if "=" in l and not l.startswith("#"))


def setup_db():
    subprocess.run(["bash", "scripts/setup_db.sh"], cwd=ROOT, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def mysql_table(sql_file):
    """Run a .sql file with the mysql client and return its boxed text output."""
    with open(os.path.join(ROOT, sql_file)) as f:
        r = subprocess.run(
            ["mysql", "--table", "-h", ENV["DB_HOST"], "-u", ENV["DB_USER"], f"-p{ENV['DB_PASSWORD']}", ENV["DB_NAME"]],
            stdin=f, capture_output=True, text=True,
        )
    return r.stdout.strip()


def md_table(rows, cols=None, fmt=None):
    if not rows:
        return "_(no rows)_"
    cols = cols or list(rows[0].keys())
    fmt = fmt or {}
    cell = lambda c, v: fmt[c](v) if c in fmt else ("NULL" if v is None else str(v).replace("|", "\\|"))
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(cell(c, r[c]) for c in cols) + " |" for r in rows]
    return "\n".join(lines)


def head_tail(text, n=12):
    lines = text.splitlines()
    return text if len(lines) <= n + 4 else "\n".join(lines[:n] + ["... (" + str(len(lines) - n - 1) + " more rows)", lines[-1]])


# ---------------------------------------------------------------- 1. fresh database, in-process measurements
print("Rebuilding database...")
setup_db()

from app import app  # noqa: E402  (imported after the rebuild so pooled connections see the new database)
from src.db import query, call_proc  # noqa: E402
from src.services import delays as delays_service  # noqa: E402

v = {"GENERATED_AT": datetime.datetime.now().strftime("%A %d %B %Y, %H:%M")}

base_tables = [r["t"] for r in query(
    "SELECT table_name t FROM information_schema.tables WHERE table_schema=DATABASE() AND table_type='BASE TABLE' ORDER BY table_name")]
views = [r["t"] for r in query("SELECT table_name t FROM information_schema.views WHERE table_schema=DATABASE() ORDER BY table_name")]
triggers = query("""SELECT trigger_name AS `Trigger`, action_timing AS `Timing`, event_manipulation AS `Event`,
                           event_object_table AS `Table` FROM information_schema.triggers
                    WHERE trigger_schema=DATABASE() ORDER BY trigger_name""")
routines = query("""SELECT routine_name AS `Procedure`, routine_type AS `Type`,
                           (SELECT COUNT(*) FROM information_schema.parameters p
                             WHERE p.specific_schema=r.routine_schema AND p.specific_name=r.routine_name) AS `Parameters`
                    FROM information_schema.routines r WHERE routine_schema=DATABASE() ORDER BY routine_name""")
v.update(N_TABLES=len(base_tables), N_VIEWS=len(views), N_TRIGGERS=len(triggers), N_ROUTINES=len(routines))
v["TRIGGERS_TABLE"] = md_table(triggers)
v["ROUTINES_TABLE"] = md_table(routines)

counts = [{"Table": t, "Rows": query(f"SELECT COUNT(*) n FROM `{t}`")[0]["n"]} for t in base_tables]
v["COUNTS_TABLE"] = md_table(counts, fmt={"Rows": lambda n: f"{n:,}"})
c = {r["Table"]: r["Rows"] for r in counts}
v["DATA_SUMMARY"] = (f"{c['airport']} airports, {c['gate']} gates, {c['aircraft']} aircraft, {c['route']} routes, "
                     f"{c['flight']:,} flights over 7 days, {c['crew']} crew, {c['passenger']:,} passengers, "
                     f"{c['booking']:,} bookings, {c['ticket']:,} tickets, {c['delay_code']} IATA delay codes")

facts = query("""SELECT
    (SELECT COUNT(*) FROM (SELECT booking_id FROM ticket GROUP BY booking_id HAVING COUNT(*) = 2) x) AS connecting_bookings,
    (SELECT COUNT(DISTINCT ca.flight_id) FROM crew_assignment ca JOIN flight f ON f.flight_id = ca.flight_id
       JOIN crew_assignment ca2 ON ca2.crew_id = ca.crew_id JOIN flight f2 ON f2.flight_id = ca2.flight_id
      WHERE f2.aircraft_id <> f.aircraft_id AND DATE(f2.sched_departure) = DATE(f.sched_departure)) AS crosslinked_flights,
    (SELECT MIN(sched_departure) FROM flight) AS first_dep, (SELECT MAX(sched_arrival) FROM flight) AS last_arr,
    (SELECT COUNT(*) FROM flight WHERE delay_minutes > 0) AS delayed_flights,
    (SELECT COUNT(*) FROM v_missed_connections) AS missed,
    (SELECT COUNT(*) FROM v_duty_breaches) AS duty,
    (SELECT COUNT(*) FROM v_curfew_risk) AS curfew""")[0]
status_mix = query("SELECT status, COUNT(*) n FROM flight GROUP BY status ORDER BY n DESC")
v["DATA_FACTS"] = "\n".join([
    f"- Schedule window: {facts['first_dep']:%a %d %b %Y %H:%M} to {facts['last_arr']:%a %d %b %Y %H:%M}.",
    f"- Flight status mix at generation time: " + ", ".join(f"{r['status']} {r['n']:,}" for r in status_mix) + ".",
    f"- Two-leg connecting bookings: {facts['connecting_bookings']:,}.",
    f"- Flights whose crew also fly a different aircraft the same day (cross-aircraft crew links): {facts['crosslinked_flights']:,}.",
    f"- With the 10 sample delays applied: {facts['delayed_flights']} flights late, {facts['missed']} missed connections, "
    f"{facts['duty']} crew duty breaches, {facts['curfew']} curfew risks.",
])

rules = query("""SELECT iata_code AS `IATA`, icao_code AS `ICAO`, city AS `City`,
                        IFNULL(CONCAT(TIME_FORMAT(open_time,'%H:%i'),'–',TIME_FORMAT(close_time,'%H:%i')),'24 h') AS `Hours`,
                        runway_slots_per_hour AS `Departures/hour`, min_connect_min AS `Min connection (min)`,
                        min_turnaround_min AS `Min turnaround (min)`,
                        (SELECT COUNT(*) FROM gate g WHERE g.airport_id = a.airport_id) AS `Gates`
                 FROM airport a ORDER BY airport_id""")
v["AIRPORT_RULES"] = md_table(rules)

# Column reference
parts = []
for t in base_tables + views:
    cols = query("""SELECT column_name c, column_type ty, is_nullable n, column_key k, column_default d, extra e
                    FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name=%s
                    ORDER BY ordinal_position""", (t,))
    fks = {r["c"]: r["ref"] for r in query("""SELECT column_name c, CONCAT(referenced_table_name,'.',referenced_column_name) ref
             FROM information_schema.key_column_usage WHERE table_schema=DATABASE() AND table_name=%s
             AND referenced_table_name IS NOT NULL""", (t,))}
    rows = []
    for col in cols:
        notes = []
        if col["c"] in fks:
            notes.append(f"FK → `{fks[col['c']]}`")
        extra = (col["e"] or "").replace("DEFAULT_GENERATED", "").strip()
        if extra:
            notes.append(extra)
        if col["d"] is not None:
            notes.append(f"default `{col['d']}`")
        rows.append({"Column": f"`{col['c']}`", "Type": f"`{col['ty']}`", "Null": col["n"],
                     "Key": col["k"] or "", "Notes": "; ".join(notes)})
    kind = "view" if t in views else f"table, {c.get(t, 0):,} rows"
    parts.append(f"#### `{t}` ({kind})\n\n" + md_table(rows))
v["COLUMNS"] = "\n\n".join(parts)

# Routes
routes = []
for r in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
    if r.endpoint == "static":
        continue
    routes.append({"Methods": ", ".join(sorted(m for m in r.methods if m in ("GET", "POST"))),
                   "URL": f"`{r.rule}`", "Endpoint": f"`{r.endpoint}`"})
v["N_ROUTES"] = len(routes)
v["ROUTES"] = md_table(routes)
v["N_TEMPLATES"] = sum(len([f for f in fs if f.endswith(".html")]) for _, _, fs in os.walk(os.path.join(ROOT, "templates")))

# Sample delays already in the seed
sample = query("""SELECT d.delay_id AS `#`, f.flight_number AS `Flight`, CONCAT(o.iata_code, '→', de.iata_code) AS `Route`,
                         dc.iata_code AS `IATA`, dr.category AS `Category`, d.sub_reason AS `Details`, d.minutes AS `Minutes`,
                         (SELECT COUNT(*) FROM delay_impact i WHERE i.delay_id = d.delay_id) AS `Other flights moved`,
                         (SELECT COALESCE(SUM(minutes_added), 0) FROM delay_impact i WHERE i.delay_id = d.delay_id) AS `Knock-on minutes`
                  FROM flight_delay d JOIN flight f USING (flight_id) JOIN route r ON r.route_id = f.route_id
                  JOIN airport o ON o.airport_id = r.origin_airport_id JOIN airport de ON de.airport_id = r.dest_airport_id
                  JOIN delay_code dc USING (code_id) JOIN delay_reason dr ON dr.reason_id = dc.reason_id
                  ORDER BY d.delay_id""")
filed = sum(r["Minutes"] for r in sample)
knock = sum(int(r["Knock-on minutes"]) for r in sample)
links = query("SELECT link, COUNT(*) n FROM delay_impact GROUP BY link ORDER BY n DESC")
v["SAMPLE_DELAYS"] = md_table(sample) + "\n\n" + (
    f"**Totals:** {filed} minutes filed directly caused **{knock:,} knock-on minutes** across "
    f"{sum(int(r['Other flights moved']) for r in sample)} other flight changes, a reactionary-to-primary ratio "
    f"of about **{knock / filed:.1f} : 1**. Knock-on changes by link: "
    + ", ".join(f"{r['link']} {r['n']}" for r in links) + ".")

# Report query outputs
qparts = []
for q, title in [("q3_ontime_performance", "q3 on-time performance"), ("q4_top_delay_causes", "q4 delay causes"),
                 ("q6_load_factor", "q6 load factor (first rows)"), ("q7_duty_status", "q7 crew duty status"),
                 ("q8_aircraft_utilisation", "q8 aircraft utilisation (first rows)")]:
    qparts.append(f"**{title}** (`database/queries/{q}.sql`)\n\n```\n{head_tail(mysql_table(f'database/queries/{q}.sql')) or '(empty result)'}\n```")
v["QUERY_RESULTS"] = "\n\n".join(qparts)

# Route smoke test (GET only; changes nothing)
client = app.test_client()
ids = query("""SELECT (SELECT MIN(flight_id) FROM flight) f, (SELECT MIN(delay_id) FROM flight_delay) d,
                      (SELECT MIN(crew_id) FROM crew) c, (SELECT MIN(passenger_id) FROM passenger) p,
                      (SELECT MIN(booking_id) FROM booking) b, (SELECT MIN(airport_id) FROM airport) a""")[0]
from src.services import admin as admin_service  # noqa: E402

urls = ["/", "/flights/", "/flights/?status=DELAYED", "/flights/?q=DEL", f"/flights/{ids['f']}", f"/flights/{ids['f']}/edit",
        "/flights/new", f"/flights/{ids['f']}/delay", "/delays/", "/delays/?open=1", f"/delays/{ids['d']}",
        f"/delays/{ids['d']}/edit", "/delays/reset", "/airports/", f"/airports/{ids['a']}/board", "/cascade/",
        f"/cascade/{ids['f']}", "/crew/", "/crew/duty", f"/crew/{ids['c']}", f"/crew/{ids['c']}/edit", "/crew/new",
        f"/crew/replacement/{ids['f']}", "/passengers/", f"/passengers/{ids['p']}", f"/passengers/{ids['p']}/edit",
        "/passengers/new", "/bookings/", f"/bookings/{ids['b']}", "/bookings/new", "/reports/", "/reports/ontime",
        "/reports/delay-causes", "/reports/load-factor", "/reports/duty-status", "/reports/utilisation", "/admin/", "/schema/"]
for e in admin_service.ENTITIES:
    urls += [f"/admin/{e}/", f"/admin/{e}/new", f"/admin/{e}/1/edit"]
for t in base_tables + views:
    urls += [f"/schema/{t}", f"/schema/{t}/rows"]
bad = [(u, s) for u in urls if (s := client.get(u).status_code) >= 400]
smoke = f"{len(urls) - len(bad)}/{len(urls)} pages returned successfully" + (f"; failures: {bad}" if bad else "")

# Worked cascade on a clean network
call_proc("reset_all_delays")
flight = query("""SELECT ft.flight_id, ft.flight_number, ft.origin, ft.dest, ft.registration, ft.std
                  FROM v_flight_times ft WHERE ft.aircraft_id = 1 AND ft.status = 'SCHEDULED'
                    AND DATE(ft.std) = CURDATE() + INTERVAL 1 DAY ORDER BY ft.std LIMIT 1""")[0]
code_id = query("SELECT code_id FROM delay_code WHERE iata_code = '41'")[0]["code_id"]
notice = {f: None for f in delays_service.NOTICE_FIELDS}
notice.update(minutes=180, code_id=code_id, sub_reason="Hydraulic leak found on walk-around", phase="AT_GATE",
              ops_status="DELAYED", reported_by="R. Mehta (Duty Manager DEL)", pax_deboarded=False,
              meal_voucher=True, compensation_eligible=True, rebooking_offered=False,
              announcement=f"Flight {flight['flight_number']} is delayed by 180 minutes.")
t0 = time.perf_counter()
delay_id = delays_service.file_delay(flight["flight_id"], notice)
elapsed = time.perf_counter() - t0
impacts = delays_service.impacts(delay_id)
affected = {flight["flight_id"]} | {i["flight_id"] for i in impacts}
summary = delays_service.affected_summary(affected)
after = query("SELECT etd FROM v_flight_times WHERE flight_id = %s", (flight["flight_id"],))[0]["etd"]
imp_rows = [{"Pass": i["pass_no"], "Flight": i["flight_number"], "Route": f"{i['origin']}→{i['dest']}",
             "Aircraft": i["registration"], "Link": i["link"], "Caused by": i["cause_flight"] or f"{i['origin']} runway slot",
             "ETD before": f"{i['old_etd']:%a %H:%M}", "ETD after": f"{i['new_etd']:%a %H:%M}", "Added": f"+{i['minutes_added']}"}
            for i in impacts]
missed_rows = [{"PNR": m["pnr"], "Passenger": m["passenger_name"], "Inbound": m["in_flight"], "Onward": m["out_flight"],
                "At": m["connect_airport"], "Connection": f"{m['connect_min']} min", "Needs": f"{m['min_connect_min']} min"}
               for m in summary["missed"]]
by_link = {}
for i in impacts:
    by_link[i["link"]] = by_link.get(i["link"], 0) + 1
v["DEMO_CASCADE"] = "\n".join([
    f"**Scenario:** starting from a network with no delays, file a 180-minute delay on **{flight['flight_number']} "
    f"({flight['origin']} → {flight['dest']}, aircraft {flight['registration']}, STD {flight['std']:%a %d %b %H:%M})** "
    f"with IATA code 41 (aircraft defect), \"Hydraulic leak found on walk-around\", phase At gate.",
    "",
    f"**Result:** the engine ran in **{elapsed:.2f} s** over all {c['flight']:,} flights and made "
    f"**{len(impacts)} knock-on changes** in {max((i['pass_no'] for i in impacts), default=0)} passes "
    f"({', '.join(f'{k} {n}' for k, n in sorted(by_link.items()))}), totalling "
    f"{sum(i['minutes_added'] for i in impacts)} knock-on minutes. {flight['flight_number']}'s ETD moved to "
    f"{after:%a %H:%M}. It reached {summary['aircraft']} aircraft and {summary['airports']} airports, "
    f"affected {summary['passengers']} passengers and broke {len(summary['missed'])} connections "
    f"({len(summary['duty'])} duty breaches, {len(summary['curfew'])} curfew risks).",
    "",
    "Every knock-on change, as logged in `delay_impact`:",
    "",
    md_table(imp_rows),
    "",
    "Passengers who now miss connections (from `v_missed_connections`; a negative connection means the onward "
    "flight now leaves before the inbound lands):",
    "",
    md_table(missed_rows),
    "",
    "How to read it: AIRCRAFT rows follow the same aircraft's day; a CREW row is where crew arriving late are "
    "rostered onto a different aircraft, so the delay jumps aircraft; SLOT rows are flights pushed into the next "
    "hour because the airport's departures for that hour were full.",
])

# ---------------------------------------------------------------- 2. test suite (each on a fresh database)
results = [f"- **Route smoke test:** {smoke}."]
for test in ["tests/test_cascade.py", "tests/test_crew_assignment.py", "tests/test_live_changes.py"]:
    print("Running", test)
    setup_db()
    r = subprocess.run([sys.executable, test], cwd=ROOT, capture_output=True, text=True)
    lines = [l for l in r.stdout.splitlines() if l.strip()]
    status = "PASS" if r.returncode == 0 else f"FAIL (exit {r.returncode})"
    if test.endswith("live_changes.py"):
        results.append(f"- **`{test}`: {status}**\n\n```\n" + "\n".join(lines) + "\n```")
    else:
        results.append(f"- **`{test}`: {status}**, output: `{lines[-1] if lines else ''}`")
v["TEST_RESULTS"] = "\n".join(results)

print("Rebuilding database (leave it clean)...")
setup_db()

# ---------------------------------------------------------------- 3. repository facts
git = subprocess.run(["git", "log", "--format=%h|%ad|%s", "--date=format:%d %b %Y %H:%M"],
                     cwd=ROOT, capture_output=True, text=True).stdout.strip().splitlines()
v["GIT_LOG"] = md_table([dict(zip(["Commit", "Date", "Message"], l.split("|", 2))) for l in git]) + \
    "\n\n(Work after the last commit is in the working tree when this file was generated.)"

SKIP_DIRS = {"venv", ".venv", ".git", "__pycache__", "screenshots", ".playwright-mcp", ".claude"}
EXT_LANG = {".sql": "sql", ".py": "python", ".html": "html", ".css": "css", ".js": "javascript",
            ".sh": "bash", ".md": "markdown", ".txt": "text", ".example": "bash", ".gitignore": "text"}
files = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
    for fn in sorted(filenames):
        rel = os.path.relpath(os.path.join(dirpath, fn), ROOT)
        if fn == ".env" or rel in (os.path.relpath(OUT, ROOT), "docs/REPORT_CONTEXT_CORE.md", "scripts/report_template.md") \
                or fn.endswith((".pyc", ".png", ".DS_Store")):
            continue
        ext = os.path.splitext(fn)[1] or fn
        if ext in EXT_LANG or fn in (".gitignore", ".env.example"):
            files.append(rel)

loc = []
for rel in files:
    if rel.startswith("docs/") or rel.endswith(".md"):
        continue
    n = sum(1 for _ in open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace"))
    loc.append({"File": f"`{rel}`", "Lines": n})
loc.sort(key=lambda r: r["File"])
v["LOC_TOTAL"] = f"{sum(r['Lines'] for r in loc):,}"
v["LOC_TABLE"] = md_table(loc) + f"\n\n**Total: {v['LOC_TOTAL']} lines** (excluding documentation)."

SHOTS = {
    "01-dashboard": "Dashboard: live headline, date, summary and the network constellation map",
    "02-dashboard-map-hover": "Map interaction: hovering Delhi draws its 19 routes and shows its tooltip",
    "03-dashboard-full": "Full dashboard: figures, airport-board shortcuts, recent delays",
    "04-flights-delayed": "Flights filtered to Delayed: scheduled times struck through, estimates in amber",
    "05-flight-detail": "Flight detail: times, crew assignment, delays filed, knock-on received, all columns",
    "06-delay-form": "Delay form filled in: IATA code, 180 minutes, auto-filled ETD/ETA/boarding, announcement, vouchers",
    "07-delay-log": "Delay log: every notice with its knock-on count and minutes",
    "08-airports": "Airports: operating rules, gates, departures today, late departures",
    "09-airport-board": "Delhi departure and arrival board with the day picker (carousel dots)",
    "10-crew-profile": "Crew profile (Team Member Card): role, name, certifications",
    "11-passengers": "Passengers list with the Section Headline Block",
    "12-booking-connection": "A two-leg connecting booking with its tickets",
    "13-reports": "Reports index",
    "14-report-ontime": "On-time performance report",
    "15-admin-airports": "Admin: airports with their timing rules (generic CRUD)",
    "16-admin-airport-edit": "Admin: editing an airport's curfew, slots, connection and turnaround times",
    "17-schema": "Schema browser: tables with exact row counts, and views",
    "18-schema-rows": "Live row browser for a table (flight_delay)",
    "19-delay-impact": "Impact page after filing the 180-min delay: figures, notice, every knock-on change, missed connections",
    "20-cascade-trace": "Cascade trace: recursive tree of the delayed flight and passengers affected",
    "21-board-after-delay": "Delhi board after the delay: changed times highlighted",
    "22-mobile-dashboard": "Dashboard at phone width (390px)",
    "23-mobile-flights": "Flights at phone width: horizontally scrolling table",
}
shot_dir = os.path.join(ROOT, "docs", "screenshots")
present = sorted(f[:-4] for f in os.listdir(shot_dir) if f.endswith(".png")) if os.path.isdir(shot_dir) else []
v["SCREENSHOTS"] = md_table([{"File": f"`docs/screenshots/{n}.png`", "Shows": SHOTS.get(n, "")} for n in present]) \
    if present else "_(no screenshots captured)_"

ORDER = ["database/", "app.py", "src/", "tests/", "scripts/", "templates/", "static/", "requirements.txt",
         ".env.example", ".gitignore", "README.md", "docs/"]
files.sort(key=lambda p: (next((i for i, pre in enumerate(ORDER) if p.startswith(pre) or p == pre), 99), p))
src = []
for n, rel in enumerate(files, 1):
    ext = os.path.splitext(rel)[1] or os.path.basename(rel)
    lang = EXT_LANG.get(ext, "text")
    body = open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace").read().rstrip()
    src.append(f"### A.{n} `{rel}`\n\n````{lang}\n{body}\n````")
v["SOURCE"] = "\n\n".join(src)

# ---------------------------------------------------------------- 4. assemble
template = open(os.path.join(ROOT, "scripts", "report_template.md"), encoding="utf-8").read()
source = v.pop("SOURCE")
out = re.sub(r"\{\{([A-Z_]+)\}\}", lambda m: str(v[m.group(1)]) if m.group(1) in v else m.group(0), template)
missing = [p for p in re.findall(r"\{\{[A-Z_]+\}\}", out) if p != "{{SOURCE}}"]
assert not missing, missing
core = out.replace("{{SOURCE}}", "_The full source code is in `docs/REPORT_CONTEXT.md` (this core version leaves it out to stay small)._")
out = out.replace("{{SOURCE}}", source)  # last, so placeholders quoted inside the source are left alone
assert ENV["DB_PASSWORD"] not in out, "database password leaked into the report"
assert ENV["DB_PASSWORD"] not in core
open(OUT, "w", encoding="utf-8").write(out)
open(OUT.replace(".md", "_CORE.md"), "w", encoding="utf-8").write(core)
print(f"Wrote {os.path.relpath(OUT, ROOT)}: {len(out.splitlines()):,} lines, {len(out) // 1024} KB "
      f"(core version {len(core.splitlines()):,} lines, {len(core) // 1024} KB), "
      f"{len(files)} source files. Tests: " + "; ".join(r.split("**")[1] for r in results[1:]))
````

### A.52 `scripts/reset_db.sh`

````bash
#!/bin/bash
set -e
cd "$(dirname "$0")/.."
exec bash scripts/setup_db.sh
````

### A.53 `scripts/run.sh`

````bash
#!/bin/bash
cd "$(dirname "$0")/.."
source .env
export FLASK_APP=app.py
python3 app.py
````

### A.54 `scripts/setup_db.sh`

````bash
#!/bin/bash
set -e
cd "$(dirname "$0")/.."
source .env

echo "==> Creating database"
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" \
  -e "DROP DATABASE IF EXISTS $DB_NAME; CREATE DATABASE $DB_NAME CHARACTER SET utf8mb4;"

echo "==> Importing schema"
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < database/01_schema.sql

echo "==> Seeding reference data"
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < database/02_seed_reference.sql

echo "==> Seeding operational data"
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < database/03_seed_operational.sql

echo "==> Installing triggers"
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < database/04_triggers.sql

echo "==> Installing procedures"
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < database/05_procedures.sql

echo "==> Installing views"
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < database/06_views.sql

echo "==> Filing sample delays"
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < database/07_seed_delays.sql

echo "==> Done"
````

### A.55 `templates/_macros.html`

````html
{% macro field(name, label, value='', type='text', required=False, options=None) %}
  <label class="field">
    <span>{{ label }}{% if required %} *{% endif %}</span>
    {% if type == 'select' %}
      <select name="{{ name }}" {% if required %}required{% endif %}>
        {% if not required %}<option value="">--</option>{% endif %}
        {% for opt in options %}
          <option value="{{ opt }}" {% if value == opt %}selected{% endif %}>{{ opt }}</option>
        {% endfor %}
      </select>
    {% elif type == 'fk' %}
      <select name="{{ name }}" {% if required %}required{% endif %}>
        <option value="">--</option>
        {% for opt in options %}
          <option value="{{ opt.id }}" {% if value is not none and value|string == opt.id|string %}selected{% endif %}>{{ opt.label }}</option>
        {% endfor %}
      </select>
    {% else %}
      <input type="{{ type }}" name="{{ name }}" value="{{ value if value is not none else '' }}" {% if type == 'number' %}step="any"{% endif %} {% if required %}required{% endif %}>
    {% endif %}
  </label>
{% endmacro %}

{# Section Headline Block (DESIGN.md): oversized headline left; amber label,
   light body copy and the page's actions on the right. #}
{% macro headline(title, label, body) %}
<header class="headline-block">
  <h1>{{ title }}</h1>
  <div>
    <span class="label">{{ label }}</span>
    <p>{{ body }}</p>
    {% if caller %}<div class="actions">{{ caller() }}</div>{% endif %}
  </div>
</header>
{% endmacro %}

{# Every column of the underlying row, read with SELECT *, so columns added by
   ALTER TABLE appear here without any template change. #}
{% macro all_columns(table, record) %}
{% if record %}
<details class="record">
  <summary>All {{ record|length }} columns in <code>{{ table }}</code></summary>
  <dl class="detail-grid">
    {% for key, value in record.items() %}<dt>{{ key }}</dt><dd>{% if value is none %}<span class="muted">NULL</span>{% else %}{{ value }}{% endif %}</dd>{% endfor %}
  </dl>
</details>
{% endif %}
{% endmacro %}
````

### A.56 `templates/_status.html`

````html
{% macro status_badge(s) %}<span class="badge badge-{{ s|lower|replace(' ', '-')|replace('_', '-') }}">{{ s|replace('_', ' ') }}</span>{% endmacro %}
{% macro times(sched, est, delay) -%}
  <span class="time">
  {%- if delay and delay > 0 -%}
    <s class="muted" aria-label="scheduled {{ sched|hhmm }}">{{ sched|hhmm }}</s> <strong class="late">{{ est|hhmm }}</strong>
  {%- else -%}{{ sched|hhmm }}{%- endif -%}
  </span>
{%- endmacro %}
````

### A.57 `templates/admin/form.html`

````html
{% extends "base.html" %}
{% from "_macros.html" import field %}
{% block title %}{{ 'Edit' if row else 'New' }} {{ cfg.item }}{% endblock %}
{% block content %}
<h1>{{ 'Edit' if row else 'New' }} {{ cfg.item }}</h1>
<form method="post" class="form">
  {% for f in fields %}
    {% if f.type == 'fk' %}
      {{ field(f.name, f.label, row[f.name] if row else '', type='fk', options=fk_options[f.name], required=f.required) }}
    {% elif f.type == 'select' %}
      {{ field(f.name, f.label, row[f.name] if row else '', type='select', options=f.options, required=f.required) }}
    {% elif f.type == 'datetime' %}
      {{ field(f.name, f.label, (row[f.name]|string)[:16] if row and row[f.name] else '', type='datetime-local', required=f.required) }}
    {% elif f.type == 'time' %}
      {{ field(f.name, f.label, row[f.name]|hhmm if row else '', type='time', required=f.required) }}
    {% elif f.type == 'date' %}
      {{ field(f.name, f.label, (row[f.name]|string) if row and row[f.name] else '', type='date', required=f.required) }}
    {% elif f.type == 'number' %}
      {{ field(f.name, f.label, row[f.name] if row else '', type='number', required=f.required) }}
    {% else %}
      {{ field(f.name, f.label, row[f.name] if row else '', required=f.required) }}
    {% endif %}
  {% endfor %}
  <button type="submit" class="btn">Save {{ cfg.item }}</button>
</form>
{% endblock %}
````

### A.58 `templates/admin/index.html`

````html
{% extends "base.html" %}
{% from "_macros.html" import headline %}
{% block title %}Admin{% endblock %}
{% block content %}
{{ headline('Reference data', '{:,}'.format(entities|length) ~ ' tables', 'The airports, gates, delay codes, routes and aircraft the rest of the operation is built on. Everything here is editable.') }}
<ul class="link-list">
  {% for key, cfg in entities.items() %}
  <li><a href="{{ url_for('admin.list_view', entity=key) }}">{{ cfg.label }}</a></li>
  {% endfor %}
</ul>
{% endblock %}
````

### A.59 `templates/admin/list.html`

````html
{% extends "base.html" %}
{% block title %}{{ cfg.label }}{% endblock %}
{% block content %}
<div class="page-header">
  <h1>{{ cfg.label }}</h1>
  <a class="btn" href="{{ url_for('admin.new', entity=entity) }}">New {{ cfg.item }}</a>
</div>
<table class="data-table">
  <thead>
    <tr>
      <th>ID</th>
      {% for f in fields %}<th>{{ f.label }}{% if f.added %} <span class="muted" title="Column added to the table after the app was built">(new)</span>{% endif %}</th>{% endfor %}
      <th></th>
    </tr>
  </thead>
  <tbody>
    {% for row in rows %}
    <tr>
      <td>{{ row[cfg.pk] }}</td>
      {% for f in fields %}<td>{% if row[f.name] is none %}—{% elif f.type == 'time' %}{{ row[f.name]|hhmm }}{% else %}{{ row[f.name] }}{% endif %}</td>{% endfor %}
      <td>
        <a class="btn btn-small" href="{{ url_for('admin.edit', entity=entity, row_id=row[cfg.pk]) }}">Edit</a>
        <form method="post" action="{{ url_for('admin.delete', entity=entity, row_id=row[cfg.pk]) }}" onsubmit="return confirm('Delete this entry?');" class="inline-form">
          <button type="submit" class="btn btn-small btn-danger">Delete</button>
        </form>
      </td>
    </tr>
    {% else %}
    <tr><td colspan="{{ fields|length + 2 }}">No entries.</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
````

### A.60 `templates/airports/board.html`

````html
{% extends "base.html" %}
{% from "_status.html" import status_badge, times %}
{% block title %}{{ airport.iata_code }} board{% endblock %}
{% block content %}
<header class="headline-block">
  <h1>{{ airport.city }}</h1>
  <div>
    <span class="label">{{ airport.iata_code }} flight board</span>
    <p>{% if airport.open_time is not none %}Open {{ airport.open_time|hhmm }} to {{ airport.close_time|hhmm }}{% else %}Open 24 hours{% endif %},
      {{ airport.runway_slots_per_hour }} departures an hour, {{ airport.min_turnaround_min }} min aircraft turnaround,
      {{ airport.min_connect_min }} min passenger connections.</p>
    <div class="actions"><a class="btn btn-ghost" href="{{ url_for('airports.list_view') }}">All airports</a></div>
  </div>
</header>

<nav class="dots" aria-label="Day">
  {% for d in dates %}
  <a class="dot-link" href="{{ url_for('airports.board', airport_id=airport.airport_id, date=d) }}"
     {% if d|string == day %}aria-current="date"{% endif %}>{{ d.strftime('%a %d') }}</a>
  {% endfor %}
</nav>

<div class="grid-2">
  <div>
    <h2>Departures</h2>
    <table class="data-table board">
      <thead><tr><th>Time</th><th>Flight</th><th>To</th><th>Gate</th><th>Status</th><th></th></tr></thead>
      <tbody>
        {% for f in departures %}
        <tr class="{% if f.display_status == 'DELAYED' %}row-delayed{% endif %}">
          <td>{{ times(f.std, f.etd, f.delay_minutes) }}</td>
          <td><a href="{{ url_for('flights.detail', flight_id=f.flight_id) }}">{{ f.flight_number }}</a></td>
          <td>{{ f.dest }}</td>
          <td>{{ f.gate_code or '—' }}</td>
          <td>{{ status_badge(f.display_status) }}</td>
          <td>{% if f.status in ('SCHEDULED', 'BOARDING', 'DEPARTED') %}<a class="btn btn-small btn-warn" href="{{ url_for('flights.delay', flight_id=f.flight_id) }}">Delay</a>{% endif %}</td>
        </tr>
        {% else %}
        <tr><td colspan="6">No departures.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  <div>
    <h2>Arrivals</h2>
    <table class="data-table board">
      <thead><tr><th>Time</th><th>Flight</th><th>From</th><th>Status</th></tr></thead>
      <tbody>
        {% for f in arrivals %}
        <tr class="{% if f.display_status == 'DELAYED' %}row-delayed{% endif %}">
          <td>{{ times(f.sta, f.eta, f.delay_minutes) }}</td>
          <td><a href="{{ url_for('flights.detail', flight_id=f.flight_id) }}">{{ f.flight_number }}</a></td>
          <td>{{ f.origin }}</td>
          <td>{{ status_badge(f.display_status) }}</td>
        </tr>
        {% else %}
        <tr><td colspan="4">No arrivals.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
````

### A.61 `templates/airports/list.html`

````html
{% extends "base.html" %}
{% from "_macros.html" import headline %}
{% block title %}Airports{% endblock %}
{% block content %}
{% call headline('Airports', '{:,}'.format(airports|length) ~ ' airports', 'Each airport\'s rules drive the cascade: aircraft turnaround, runway departures per hour, passenger connection time and curfew hours.') %}
  <a class="btn" href="{{ url_for('admin.new', entity='airport') }}">New airport</a>
  <a class="btn btn-ghost" href="{{ url_for('admin.list_view', entity='gate') }}">Manage gates</a>
{% endcall %}
<table class="data-table">
  <thead><tr><th>Airport</th><th>City</th><th>Hours</th><th>Slots/h</th><th>Turnaround</th><th>Min connect</th><th>Gates</th><th>Departures today</th><th>Delayed</th><th></th></tr></thead>
  <tbody>
    {% for a in airports %}
    <tr>
      <td><strong>{{ a.iata_code }}</strong> <span class="muted">{{ a.icao_code }}</span></td>
      <td>{{ a.city }}</td>
      <td>{% if a.open_time is not none %}{{ a.open_time|hhmm }}–{{ a.close_time|hhmm }}{% else %}24 h{% endif %}</td>
      <td>{{ a.runway_slots_per_hour }}</td>
      <td>{{ a.min_turnaround_min }} min</td>
      <td>{{ a.min_connect_min }} min</td>
      <td>{{ a.gates }}</td>
      <td>{{ a.departures_today }}</td>
      <td>{% if a.delayed_departures %}<span class="late">{{ a.delayed_departures }}</span>{% else %}0{% endif %}</td>
      <td class="nowrap">
        <a class="btn btn-small" href="{{ url_for('airports.board', airport_id=a.airport_id) }}">Board</a>
        <a class="btn btn-small btn-ghost" href="{{ url_for('admin.edit', entity='airport', row_id=a.airport_id) }}">Edit</a>
      </td>
    </tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
````

### A.62 `templates/base.html`

````html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}Airline Cascades{% endblock %} · Cascades</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@200;400;600&display=swap" rel="stylesheet">
  <link rel="icon" href="{{ url_for('static', filename='img/mark.svg') }}" type="image/svg+xml">
  <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
  <canvas id="ambient-field" aria-hidden="true"></canvas>
  <header class="topbar">
    <a class="brand" href="{{ url_for('dashboard.index') }}" aria-label="Cascades, operations dashboard">
      <svg viewBox="0 0 32 32" aria-hidden="true">
        <defs><linearGradient id="mark" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stop-color="#8052ff"/><stop offset="1" stop-color="#15846e"/>
        </linearGradient></defs>
        <path d="M16 2 30 28H2z" fill="url(#mark)"/>
        <path d="M16 13 22.5 25h-13z" fill="#000"/>
      </svg>
      Cascades
    </a>
    <nav aria-label="Main">
      {% set here = request.blueprint %}
      {% for bp, endpoint, label in [
        ('dashboard', 'dashboard.index', 'Dashboard'),
        ('flights', 'flights.list_view', 'Flights'),
        ('delays', 'delays.list_view', 'Delays'),
        ('airports', 'airports.list_view', 'Airports'),
        ('cascade', 'cascade.index', 'Cascade'),
        ('crew', 'crew.list_view', 'Crew'),
        ('passengers', 'passengers.list_view', 'Passengers'),
        ('bookings', 'bookings.list_view', 'Bookings'),
        ('reports', 'reports.index', 'Reports'),
        ('admin', 'admin.index', 'Admin'),
        ('schema', 'schema.index', 'Schema'),
      ] %}
      <a href="{{ url_for(endpoint) }}" {% if here == bp %}aria-current="page"{% endif %}>{{ label }}</a>
      {% endfor %}
    </nav>
    <div class="topbar-end">
      {% if delayed_now %}
      <a class="nav-late" href="{{ url_for('flights.list_view', status='DELAYED') }}">{{ delayed_now }} late</a>
      {% endif %}
      <a class="btn" href="{{ url_for('flights.list_view', status='SCHEDULED') }}">File a delay</a>
    </div>
  </header>

  <main class="container">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        <ul class="flashes" role="status">
          {% for category, message in messages %}
            <li class="flash flash-{{ category }}">{{ message }}</li>
          {% endfor %}
        </ul>
      {% endif %}
    {% endwith %}

    {% block content %}{% endblock %}
  </main>
  <script src="{{ url_for('static', filename='js/ambient.js') }}" defer></script>
</body>
</html>
````

### A.63 `templates/bookings/detail.html`

````html
{% extends "base.html" %}
{% from "_macros.html" import all_columns %}
{% block title %}Booking {{ booking.pnr }}{% endblock %}
{% block content %}
<div class="page-header">
  <h1>Booking {{ booking.pnr }}</h1>
  <div class="actions">
    {% if booking.status != 'CANCELLED' %}
    <form method="post" action="{{ url_for('bookings.cancel', booking_id=booking.booking_id) }}" onsubmit="return confirm('Cancel this booking?');" class="inline-form">
      <button type="submit" class="btn btn-danger">Cancel booking</button>
    </form>
    {% endif %}
  </div>
</div>
<dl class="detail-grid">
  <dt>Passenger</dt><dd>{{ booking.passenger_name }}</dd>
  <dt>Status</dt><dd>{{ booking.status|human }}</dd>
  <dt>Booking date</dt><dd>{{ booking.booking_date|when }}</dd>
</dl>

<h2>Tickets</h2>
<table class="data-table">
  <thead><tr><th>Flight</th><th>Seat</th><th>Class</th><th>Fare</th><th>Checked in</th><th></th></tr></thead>
  <tbody>
    {% for t in tickets %}
    <tr>
      <td>{{ t.flight_number }}</td>
      <td>{{ t.seat_no }}</td>
      <td>{{ t.class|human }}</td>
      <td>{{ t.fare }}</td>
      <td>{{ (t.checked_in_at|when) or '—' }}</td>
      <td>
        {% if not t.checked_in_at %}
        <form method="post" action="{{ url_for('bookings.checkin', ticket_id=t.ticket_id) }}" class="inline-form">
          <input type="hidden" name="booking_id" value="{{ booking.booking_id }}">
          <button type="submit" class="btn btn-small">Check in</button>
        </form>
        {% endif %}
      </td>
    </tr>
    {% else %}
    <tr><td colspan="6">No tickets.</td></tr>
    {% endfor %}
  </tbody>
</table>

<h2>Add another ticket</h2>
<form method="post" action="{{ url_for('bookings.add_ticket', booking_id=booking.booking_id) }}" class="form-inline">
  <select name="flight_id" required>
    {% for f in flights %}
    <option value="{{ f.flight_id }}">{{ f.flight_number }} ({{ f.origin }} → {{ f.dest }})</option>
    {% endfor %}
  </select>
  <input type="text" name="seat_no" placeholder="Seat" required>
  <select name="ticket_class" required>
    {% for c in enum_values('ticket', 'class') %}
    <option value="{{ c }}">{{ c|human }}</option>
    {% endfor %}
  </select>
  <input type="number" step="0.01" name="fare" placeholder="Fare" required>
  <button type="submit" class="btn">Add ticket</button>
</form>

{{ all_columns('booking', record) }}
{% endblock %}
````

### A.64 `templates/bookings/form.html`

````html
{% extends "base.html" %}
{% from "_macros.html" import field %}
{% block title %}New Booking{% endblock %}
{% block content %}
<h1>New Booking</h1>
<p>Creates a booking with its first ticket in one step (calls the book_ticket procedure).</p>
<form method="post" class="form">
  <label class="field">
    <span>Passenger *</span>
    <select name="passenger_id" required>
      {% for p in passengers %}
      <option value="{{ p.passenger_id }}">{{ p.name }}</option>
      {% endfor %}
    </select>
  </label>
  <label class="field">
    <span>Flight *</span>
    <select name="flight_id" required>
      {% for f in flights %}
      <option value="{{ f.flight_id }}">{{ f.flight_number }} ({{ f.origin }} → {{ f.dest }})</option>
      {% endfor %}
    </select>
  </label>
  {{ field('seat_no', 'Seat No.', '', required=True) }}
  {{ field('ticket_class', 'Class', '', type='select', options=enum_values('ticket', 'class'), required=True) }}
  {{ field('fare', 'Fare', '', type='number', required=True) }}
  <button type="submit" class="btn">Book</button>
</form>
{% endblock %}
````

### A.65 `templates/bookings/list.html`

````html
{% extends "base.html" %}
{% from "_macros.html" import headline %}
{% block title %}Bookings{% endblock %}
{% block content %}
{% call headline('Bookings', '{:,}'.format(bookings|length) ~ ' bookings', 'Each booking holds one or more tickets. Two-ticket bookings are connections, and they break when the first flight runs late.') %}
  <a class="btn" href="{{ url_for('bookings.new') }}">New booking</a>
{% endcall %}
<form method="get" class="filter-bar">
  <select name="status">
    <option value="">All statuses</option>
    {% for s in enum_values('booking', 'status') %}
    <option value="{{ s }}" {% if status == s %}selected{% endif %}>{{ s|human }}</option>
    {% endfor %}
  </select>
  <button type="submit" class="btn btn-ghost">Filter</button>
</form>
<table class="data-table">
  <thead><tr><th>PNR</th><th>Passenger</th><th>Date</th><th>Status</th></tr></thead>
  <tbody>
    {% for b in bookings %}
    <tr>
      <td><a href="{{ url_for('bookings.detail', booking_id=b.booking_id) }}">{{ b.pnr }}</a></td>
      <td>{{ b.passenger_name }}</td>
      <td>{{ b.booking_date|when }}</td>
      <td>{{ b.status|human }}</td>
    </tr>
    {% else %}
    <tr><td colspan="4">No bookings found.</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
````

### A.66 `templates/cascade/index.html`

````html
{% extends "base.html" %}
{% from "_macros.html" import headline %}
{% block title %}Cascade trace{% endblock %}
{% block content %}
{% call headline('Cascade trace', '{:,}'.format(flights|length) ~ ' flights',
                  'Follow a delay downstream: pick a flight to see every flight it held up, level by level, through a recursive query.') %}
  <a class="btn btn-danger" href="{{ url_for('delays.reset') }}">Reset all delays</a>
{% endcall %}
<table class="data-table">
  <thead><tr><th>Flight</th><th>Route</th><th>Departure</th><th>Delay</th><th></th></tr></thead>
  <tbody>
    {% for f in flights %}
    <tr>
      <td>{{ f.flight_number }}</td>
      <td>{{ f.origin }} → {{ f.dest }}</td>
      <td>{{ f.sched_departure|when }}</td>
      <td>{{ f.delay_minutes }} min</td>
      <td><a class="btn btn-small" href="{{ url_for('cascade.trace', flight_id=f.flight_id) }}">Trace</a></td>
    </tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
````

### A.67 `templates/cascade/trace.html`

````html
{% extends "base.html" %}
{% block title %}Cascade Trace — {{ flight.flight_number }}{% endblock %}
{% block content %}
<h1>Cascade Trace — {{ flight.flight_number }}</h1>

<p><a class="btn btn-primary-warn" href="{{ url_for('flights.delay', flight_id=flight.flight_id) }}">Delay {{ flight.flight_number }}</a>
  <span class="hint">The tree follows the aircraft and crew links recorded as each flight's knock-on source (parent_flight_id). The full impact of each delay, including runway-slot effects, is on its impact page.</span></p>

<h2>Cascade tree (root: {{ flight.flight_number }})</h2>
<table class="data-table">
  <thead><tr><th>Depth</th><th>Flight</th><th>Scheduled departure</th><th>Delay (min)</th></tr></thead>
  <tbody>
    {% for row in tree %}
    <tr>
      <td>{{ row.cascade_depth }}</td>
      <td><a href="{{ url_for('flights.detail', flight_id=row.flight_id) }}">{{ row.flight_number }}</a></td>
      <td>{{ row.sched_departure|when }}</td>
      <td>{{ row.delay_minutes }}</td>
    </tr>
    {% else %}
    <tr><td colspan="4">No cascade — this flight has no downstream delays.</td></tr>
    {% endfor %}
  </tbody>
</table>

<h2>Passengers affected</h2>
<table class="data-table">
  <thead><tr><th>Passenger</th><th>Email</th><th>Flight</th><th>Seat</th><th>Class</th></tr></thead>
  <tbody>
    {% for p in passengers %}
    <tr><td>{{ p.name }}</td><td>{{ p.email or '—' }}</td><td>{{ p.flight_id }}</td><td>{{ p.seat_no }}</td><td>{{ p.class|human }}</td></tr>
    {% else %}
    <tr><td colspan="5">No passengers affected.</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
````

### A.68 `templates/crew/detail.html`

````html
{% extends "base.html" %}
{% from "_macros.html" import all_columns %}
{% block title %}{{ crew.name }}{% endblock %}
{% block content %}
<div class="page-header">
  <div class="person">
    <span class="role">{{ crew.role|human }}, {{ crew.base }}</span>
    <h1>{{ crew.name }}</h1>
  </div>
  <div class="actions">
    <a class="btn btn-ghost" href="{{ url_for('crew.edit', crew_id=crew.crew_id) }}">Edit</a>
    <form method="post" action="{{ url_for('crew.delete', crew_id=crew.crew_id) }}" onsubmit="return confirm('Delete this crew member?');" class="inline-form">
      <button type="submit" class="btn btn-danger">Delete</button>
    </form>
  </div>
</div>
<dl class="detail-grid">
  <dt>Base</dt><dd>{{ crew.base }}</dd>
  <dt>Hired</dt><dd>{{ crew.hire_date|when }}</dd>
  <dt>Terminated</dt><dd>{{ (crew.terminated_at|when) or '—' }}</dd>
</dl>

<h2>Certifications</h2>
<table class="data-table">
  <thead><tr><th>Aircraft Type</th><th>Certified</th><th>Expires</th><th></th></tr></thead>
  <tbody>
    {% for c in certs %}
    <tr>
      <td>{{ c.manufacturer }} {{ c.model }}</td>
      <td>{{ c.certified_date|when }}</td>
      <td>{{ c.expiry_date|when }}</td>
      <td>
        <form method="post" action="{{ url_for('crew.decertify', crew_id=crew.crew_id, type_id=c.type_id) }}" class="inline-form">
          <button type="submit" class="btn btn-small">Remove</button>
        </form>
      </td>
    </tr>
    {% else %}
    <tr><td colspan="4">No certifications.</td></tr>
    {% endfor %}
  </tbody>
</table>

<form method="post" action="{{ url_for('crew.certify', crew_id=crew.crew_id) }}" class="form-inline">
  <select name="type_id" required>
    {% for t in aircraft_types %}
    <option value="{{ t.id }}">{{ t.label }}</option>
    {% endfor %}
  </select>
  <input type="date" name="certified_date" required>
  <input type="date" name="expiry_date" required>
  <button type="submit" class="btn">Add certification</button>
</form>

{{ all_columns('crew', record) }}
{% endblock %}
````

### A.69 `templates/crew/duty.html`

````html
{% extends "base.html" %}
{% block title %}Duty Status{% endblock %}
{% block content %}
<h1>Crew nearing duty limit today</h1>
<table class="data-table">
  <thead><tr><th>Name</th><th>Role</th><th>Hours on duty</th><th>Hours flown</th><th>Hours remaining</th></tr></thead>
  <tbody>
    {% for d in duty %}
    <tr>
      <td>{{ d.name }}</td>
      <td>{{ d.role|human }}</td>
      <td>{{ d.hours_on_duty }}</td>
      <td>{{ d.hours_flown }}</td>
      <td>{{ d.hours_remaining }}</td>
    </tr>
    {% else %}
    <tr><td colspan="5">No crew near the duty limit today.</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
````

### A.70 `templates/crew/form.html`

````html
{% extends "base.html" %}
{% from "_macros.html" import field %}
{% block title %}{{ 'Edit' if crew else 'New' }} Crew Member{% endblock %}
{% block content %}
<h1>{{ 'Edit' if crew else 'New' }} Crew Member</h1>
<form method="post" class="form">
  {{ field('name', 'Name', crew.name if crew else '', required=True) }}
  {{ field('role', 'Role', crew.role if crew else '', type='select', options=enum_values('crew', 'role'), required=True) }}
  {{ field('base_airport_id', 'Base Airport', crew.base_airport_id if crew else '', type='fk', options=airports, required=True) }}
  {{ field('hire_date', 'Hire Date', crew.hire_date if crew else '', type='date', required=True) }}
  {% if crew %}
  {{ field('terminated_at', 'Terminated At', (crew.terminated_at|string)[:16] if crew.terminated_at else '', type='datetime-local') }}
  {% endif %}
  <button type="submit" class="btn">Save</button>
</form>
{% endblock %}
````

### A.71 `templates/crew/list.html`

````html
{% extends "base.html" %}
{% from "_macros.html" import headline %}
{% block title %}Crew{% endblock %}
{% block content %}
{% call headline('Crew', '{:,}'.format(crew|length) ~ ' crew members', 'Pilots and cabin crew, their bases and certifications. Crew who switch aircraft mid-day carry delays from one plane to another.') %}
  <a class="btn" href="{{ url_for('crew.new') }}">New crew member</a>
{% endcall %}
<form method="get" class="filter-bar">
  <select name="role">
    <option value="">All roles</option>
    {% for r in enum_values('crew', 'role') %}
    <option value="{{ r }}" {% if role == r %}selected{% endif %}>{{ r|human }}</option>
    {% endfor %}
  </select>
  <button type="submit" class="btn btn-ghost">Filter</button>
  <a class="btn btn-ghost" href="{{ url_for('crew.duty') }}">Duty status</a>
</form>
<table class="data-table">
  <thead><tr><th>Name</th><th>Role</th><th>Base</th><th>Hired</th><th>Status</th></tr></thead>
  <tbody>
    {% for c in crew %}
    <tr>
      <td><a href="{{ url_for('crew.detail', crew_id=c.crew_id) }}">{{ c.name }}</a></td>
      <td>{{ c.role|human }}</td>
      <td>{{ c.base }}</td>
      <td>{{ c.hire_date|when }}</td>
      <td>{{ 'Terminated' if c.terminated_at else 'Active' }}</td>
    </tr>
    {% else %}
    <tr><td colspan="5">No crew found.</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
````

### A.72 `templates/crew/replacement.html`

````html
{% extends "base.html" %}
{% block title %}Replacement Crew{% endblock %}
{% block content %}
<h1>Eligible replacement crew for flight #{{ flight_id }}</h1>
<p>Certified on the aircraft type, based at the origin airport, not already assigned
   to an overlapping flight, and under the 11-hour daily duty limit.</p>
<table class="data-table">
  <thead><tr><th>Name</th><th>Role</th></tr></thead>
  <tbody>
    {% for c in candidates %}
    <tr><td>{{ c.name }}</td><td>{{ c.role|human }}</td></tr>
    {% else %}
    <tr><td colspan="2">No eligible replacement crew found.</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
````

### A.73 `templates/dashboard/index.html`

````html
{% extends "base.html" %}
{% block title %}Operations{% endblock %}
{% block content %}
<section class="hero">
  <div>
    {% if summary.delayed_now %}
    <h1>{{ summary.delayed_now }} {{ 'flight' if summary.delayed_now == 1 else 'flights' }} running late.</h1>
    {% else %}
    <h1>Every flight on schedule.</h1>
    {% endif %}
    <span class="label">{{ today.strftime('%A %d %B') }}</span>
    <p>{{ '{:,}'.format(summary.flights_this_week) }} flights across {{ airports|length }} airports this week.
      A late flight holds up its aircraft's next legs, the crew waiting for it, the gate it sits at and the
      runway slot it needed. File a delay and see how far it reaches.</p>
    <a class="btn" href="{{ url_for('flights.list_view', status='SCHEDULED') }}">File a delay</a>
  </div>
  <div class="hero-visual">
  <div class="constellation" id="constellation"
       data-airports='{{ network|tojson }}' data-routes='{{ network_routes|tojson }}'>
    <canvas aria-hidden="true"></canvas>
    <div class="constellation-tip" aria-hidden="true"></div>
  </div>
  <p class="hint constellation-legend">Hover an airport to trace its routes; click to open its board.</p>
  </div>
</section>

<div class="stat-grid">
  <div class="stat-card"><span class="stat-value">{{ summary.flights_today }}</span><span class="stat-label">flights today</span></div>
  <div class="stat-card"><span class="stat-value {% if summary.delayed_now %}late{% endif %}">{{ summary.delayed_now }}</span><span class="stat-label">running late</span></div>
  <div class="stat-card"><span class="stat-value">{{ summary.knock_on_flights }}</span><span class="stat-label">late because of another flight</span></div>
  <div class="stat-card"><span class="stat-value {% if flags.missed %}late{% endif %}">{{ flags.missed }}</span><span class="stat-label">missed connections</span></div>
  <div class="stat-card"><span class="stat-value {% if flags.duty %}late{% endif %}">{{ flags.duty }}</span><span class="stat-label">crew over duty limit</span></div>
  <div class="stat-card"><span class="stat-value {% if flags.curfew %}late{% endif %}">{{ flags.curfew }}</span><span class="stat-label">curfew risks</span></div>
  <div class="stat-card"><span class="stat-value">{{ summary.active_aircraft }}</span><span class="stat-label">aircraft in service</span></div>
  <div class="stat-card"><span class="stat-value">{{ '{:,}'.format(summary.confirmed_bookings) }}</span><span class="stat-label">confirmed bookings</span></div>
</div>

<h2>Airport boards</h2>
<nav class="chip-row" aria-label="Airport boards">
  {% for a in airports %}
  <a class="chip {% if a.delayed_departures %}chip-late{% endif %}" href="{{ url_for('airports.board', airport_id=a.airport_id) }}"
     title="{{ a.city }}{% if a.delayed_departures %}, {{ a.delayed_departures }} late departures{% endif %}">
    {{ a.iata_code }}{% if a.delayed_departures %} {{ a.delayed_departures }}{% endif %}
  </a>
  {% endfor %}
</nav>

<div class="page-header">
  <h2>Recent delays</h2>
  <a class="btn btn-ghost" href="{{ url_for('delays.list_view') }}">Full delay log</a>
</div>
<table class="data-table">
  <thead><tr><th>Flight</th><th>Reason</th><th>Minutes</th><th>Other flights delayed</th><th>Filed</th><th></th></tr></thead>
  <tbody>
    {% for d in recent_delays %}
    <tr>
      <td>{{ d.flight_number }}</td>
      <td>{{ d.category|human }}</td>
      <td class="late">+{{ d.minutes }}</td>
      <td>{{ d.knock_on }}</td>
      <td class="muted">{{ d.recorded_at.strftime('%d %b %H:%M') }}</td>
      <td><a class="btn btn-small" href="{{ url_for('delays.detail', delay_id=d.delay_id) }}">Impact</a></td>
    </tr>
    {% else %}
    <tr><td colspan="6">No delays filed. Press Delay on any flight to file one.</td></tr>
    {% endfor %}
  </tbody>
</table>

<script src="{{ url_for('static', filename='js/constellation.js') }}" defer></script>
{% endblock %}
````

### A.74 `templates/delays/detail.html`

````html
{% extends "base.html" %}
{% from "_macros.html" import all_columns %}
{% from "_status.html" import status_badge %}
{% block title %}Delay #{{ notice.delay_id }} impact{% endblock %}
{% block content %}
<div class="page-header">
  <h1>Delay #{{ notice.delay_id }} — {{ notice.flight_number }} {{ notice.origin }} → {{ notice.dest }}</h1>
  <div class="actions">
    <a class="btn btn-ghost" href="{{ url_for('flights.detail', flight_id=notice.flight_id) }}">Flight</a>
    <a class="btn btn-ghost" href="{{ url_for('delays.edit', delay_id=notice.delay_id) }}">Edit notice</a>
    {% if not notice.resolved_at %}
    <form method="post" action="{{ url_for('delays.resolve', delay_id=notice.delay_id) }}" class="inline-form">
      <button type="submit" class="btn">Mark resolved</button>
    </form>
    {% endif %}
  </div>
</div>

<div class="stat-grid">
  <div class="stat-card"><span class="stat-value late">+{{ notice.minutes }}</span><span class="stat-label">minutes on {{ notice.flight_number }}</span></div>
  <div class="stat-card"><span class="stat-value">{{ impacts|length }}</span><span class="stat-label">other flights delayed</span></div>
  <div class="stat-card"><span class="stat-value">{{ knock_on_minutes }}</span><span class="stat-label">knock-on minutes</span></div>
  <div class="stat-card"><span class="stat-value">{{ summary.aircraft }}</span><span class="stat-label">aircraft affected</span></div>
  <div class="stat-card"><span class="stat-value">{{ summary.airports }}</span><span class="stat-label">airports affected</span></div>
  <div class="stat-card"><span class="stat-value">{{ summary.passengers }}</span><span class="stat-label">passengers affected</span></div>
  <div class="stat-card"><span class="stat-value {% if summary.missed %}late{% endif %}">{{ summary.missed|length }}</span><span class="stat-label">missed connections</span></div>
</div>

<h2>Notice</h2>
<dl class="detail-grid">
  <dt>Reason</dt><dd>{{ notice.category|human }}, IATA {{ notice.iata_code }}: {{ notice.code_description }}</dd>
  <dt>Details</dt><dd>{{ notice.sub_reason or '—' }}</dd>
  <dt>Phase / status</dt><dd>{{ notice.phase|human }}, {{ notice.ops_status|human|lower }}</dd>
  <dt>Flight now</dt><dd>{{ status_badge(notice.display_status) }} STD {{ notice.std|when }} → ETD <strong class="late">{{ notice.etd|when }}</strong>, ETA {{ notice.eta|when }}</dd>
  <dt>Gate change</dt><dd>{{ notice.new_gate_code or 'No' }}</dd>
  <dt>New boarding time</dt><dd>{{ (notice.new_boarding_time|when) or '—' }}</dd>
  <dt>Aircraft swap</dt><dd>{{ notice.swap_registration or 'No' }}</dd>
  <dt>Passengers deboarded</dt><dd>{{ 'Yes' if notice.pax_deboarded else 'No' }}</dd>
  <dt>Announcement</dt><dd>{{ notice.announcement or '—' }}</dd>
  <dt>Care</dt><dd>
    {% if notice.meal_voucher %}<span class="badge">Meal voucher</span>{% endif %}
    {% if notice.compensation_eligible %}<span class="badge">Compensation</span>{% endif %}
    {% if notice.rebooking_offered %}<span class="badge">Free rebooking</span>{% endif %}
    {% if not (notice.meal_voucher or notice.compensation_eligible or notice.rebooking_offered) %}—{% endif %}
  </dd>
  <dt>Reported by</dt><dd>{{ notice.reported_by or '—' }} at {{ notice.recorded_at|when }}</dd>
  <dt>Remarks</dt><dd>{{ notice.remarks or '—' }}</dd>
  <dt>Resolved</dt><dd>{{ (notice.resolved_at|when) or 'Open' }}</dd>
</dl>

<h2>Knock-on effects across the network</h2>
<p class="hint">
  {% for link, n in by_link|dictsort %}<span class="badge badge-link-{{ link|lower }}">{{ link }} × {{ n }}</span> {% endfor %}
</p>
<p class="hint">Aircraft: the same plane's next leg. Crew: waiting for crew arriving on a late flight. Gate: the gate is still occupied. Slot: the airport's departures for that hour are full.
</p>
<table class="data-table">
  <thead><tr><th>Pass</th><th>Flight</th><th>Route</th><th>Aircraft</th><th>Link</th><th>Caused by</th><th>ETD before</th><th>ETD after</th><th>Added</th><th>Total delay now</th></tr></thead>
  <tbody>
    {% for i in impacts %}
    <tr>
      <td>{{ i.pass_no }}</td>
      <td><a href="{{ url_for('flights.detail', flight_id=i.flight_id) }}">{{ i.flight_number }}</a></td>
      <td>{{ i.origin }} → {{ i.dest }}</td>
      <td>{{ i.registration }}</td>
      <td><span class="badge badge-link-{{ i.link|lower }}">{{ i.link }}</span></td>
      <td>{% if i.cause_flight_id %}<a href="{{ url_for('flights.detail', flight_id=i.cause_flight_id) }}">{{ i.cause_flight }}</a>{% else %}{{ i.origin }} runway{% endif %}</td>
      <td>{{ i.old_etd|when }}</td>
      <td class="late">{{ i.new_etd|when }}</td>
      <td>+{{ i.minutes_added }}</td>
      <td>{{ i.delay_minutes }} min</td>
    </tr>
    {% else %}
    <tr><td colspan="10">No knock-on effects — the network absorbed this delay.</td></tr>
    {% endfor %}
  </tbody>
</table>

<h2>Missed passenger connections</h2>
<table class="data-table">
  <thead><tr><th>PNR</th><th>Passenger</th><th>Inbound</th><th>Arrives</th><th>Onward</th><th>Departs</th><th>At</th><th>Connection</th></tr></thead>
  <tbody>
    {% for m in summary.missed %}
    <tr>
      <td><a href="{{ url_for('bookings.detail', booking_id=m.booking_id) }}">{{ m.pnr }}</a></td>
      <td>{{ m.passenger_name }}</td>
      <td>{{ m.in_flight }}</td><td>{{ m.in_eta|when }}</td>
      <td>{{ m.out_flight }}</td><td>{{ m.out_etd|when }}</td>
      <td>{{ m.connect_airport }}</td>
      <td class="late">{{ m.connect_min }} min (needs {{ m.min_connect_min }})</td>
    </tr>
    {% else %}
    <tr><td colspan="8">No connections broken.</td></tr>
    {% endfor %}
  </tbody>
</table>

<div class="grid-2">
  <div>
    <h2>Crew duty-limit breaches (&gt; 13 h)</h2>
    <table class="data-table">
      <thead><tr><th>Crew</th><th>Role</th><th>Date</th><th>Duty</th></tr></thead>
      <tbody>
        {% for d in summary.duty %}
        <tr><td><a href="{{ url_for('crew.detail', crew_id=d.crew_id) }}">{{ d.name }}</a></td><td>{{ d.role|human }}</td><td>{{ d.duty_date|when }}</td><td class="late">{{ d.duty_hours }} h</td></tr>
        {% else %}
        <tr><td colspan="4">None.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  <div>
    <h2>Curfew risks</h2>
    <table class="data-table">
      <thead><tr><th>Flight</th><th>Side</th><th>Airport</th><th>Time</th><th>Open</th></tr></thead>
      <tbody>
        {% for c in summary.curfew %}
        <tr><td>{{ c.flight_number }}</td><td>{{ c.side|title }}</td><td>{{ c.airport }}</td><td class="late">{{ c.at_time|when }}</td><td>{{ c.open_time|hhmm }}–{{ c.close_time|hhmm }}</td></tr>
        {% else %}
        <tr><td colspan="5">None.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>

{{ all_columns('flight_delay', record) }}
{% endblock %}
````

### A.75 `templates/delays/edit.html`

````html
{% extends "base.html" %}
{% block title %}Edit delay #{{ notice.delay_id }}{% endblock %}
{% block content %}
<h1>Edit delay #{{ notice.delay_id }} — {{ notice.flight_number }}</h1>
<p class="hint">Timing ({{ notice.minutes }} min, IATA {{ notice.iata_code }}) is locked once the delay has cascaded. To add more time, file another delay on the flight.</p>
<form method="post" class="form form-wide">
  <label class="field"><span>Details / sub-reason</span><input type="text" name="sub_reason" maxlength="200" value="{{ notice.sub_reason or '' }}"></label>
  <label class="field"><span>Public announcement</span><textarea name="announcement" rows="3" maxlength="500">{{ notice.announcement or '' }}</textarea></label>
  <div class="checks">
    <label class="check"><input type="checkbox" name="pax_deboarded" {% if notice.pax_deboarded %}checked{% endif %}> Passengers deboarded</label>
    <label class="check"><input type="checkbox" name="meal_voucher" {% if notice.meal_voucher %}checked{% endif %}> Meal voucher</label>
    <label class="check"><input type="checkbox" name="compensation_eligible" {% if notice.compensation_eligible %}checked{% endif %}> Compensation eligible</label>
    <label class="check"><input type="checkbox" name="rebooking_offered" {% if notice.rebooking_offered %}checked{% endif %}> Free rebooking offered</label>
  </div>
  <label class="field"><span>Reported by *</span><input type="text" name="reported_by" maxlength="80" required value="{{ notice.reported_by or '' }}"></label>
  <label class="field"><span>Internal remarks</span><input type="text" name="remarks" maxlength="500" value="{{ notice.remarks or '' }}"></label>
  <button type="submit" class="btn">Save</button>
</form>
{% endblock %}
````

### A.76 `templates/delays/form.html`

````html
{% extends "base.html" %}
{% from "_status.html" import status_badge %}
{% block title %}Delay {{ flight.flight_number }}{% endblock %}
{% block content %}
<div class="page-header">
  <div>
    <h1>Delay {{ flight.flight_number }}</h1>
    <p>{{ flight.origin_city }} to {{ flight.dest_city }}. Filing this moves every flight that depends on it.</p>
  </div>
  <a class="btn btn-ghost" href="{{ url_for('flights.detail', flight_id=flight.flight_id) }}">Back to flight</a>
</div>

<dl class="detail-grid">
  <dt>Status</dt><dd>{{ status_badge(flight.display_status) }}</dd>
  <dt>Aircraft</dt><dd>{{ flight.registration }}</dd>
  <dt>Gate</dt><dd>{{ flight.gate_code or '—' }}</dd>
  <dt>Scheduled departure</dt><dd>{{ flight.std|when }}</dd>
  <dt>Current estimate (ETD / ETA)</dt><dd>{{ flight.etd|when }} / {{ flight.eta|when }}{% if flight.delay_minutes %} <span class="late">(+{{ flight.delay_minutes }} min already)</span>{% endif %}</dd>
</dl>

<form method="post" class="form form-wide" id="delay-form"
      data-etd="{{ flight.etd.strftime('%Y-%m-%dT%H:%M') }}"
      data-boarding="{{ flight.boarding_start.strftime('%Y-%m-%dT%H:%M') if flight.boarding_start else '' }}"
      data-delay="{{ flight.delay_minutes }}"
      data-flight="{{ flight.flight_number }}" data-dest="{{ flight.dest_city }}">

  <fieldset>
    <legend>Delay notice</legend>
    <div class="grid-2">
      <label class="field"><span>IATA delay code *</span>
        <select name="code_id" required>
          <option value="">— choose a reason —</option>
          {% for cat, group in codes|groupby('category') %}
          <optgroup label="{{ cat|human }}">
            {% for c in group %}
            <option value="{{ c.id }}" {% if values.get('code_id') == c.id|string %}selected{% endif %}>{{ c.iata_code }} — {{ c.description }}</option>
            {% endfor %}
          </optgroup>
          {% endfor %}
        </select>
      </label>
      <label class="field"><span>Details / sub-reason</span>
        <input type="text" name="sub_reason" maxlength="200" value="{{ values.get('sub_reason', '') }}" placeholder="e.g. Hydraulic leak found on walk-around">
      </label>
      <label class="field"><span>Delay (minutes) *</span>
        <input type="number" name="minutes" id="minutes" min="0" max="1440" value="{{ values.get('minutes', '') }}" placeholder="e.g. 90">
      </label>
      <label class="field"><span>New estimated departure (ETD)</span>
        <input type="datetime-local" name="new_etd" id="new_etd" value="{{ values.get('new_etd', '') }}">
      </label>
      <label class="field"><span>Phase when delay occurred *</span>
        <select name="phase" required>
          {% for p in phases %}<option value="{{ p }}" {% if values.get('phase') == p %}selected{% endif %}>{{ p|human }}</option>{% endfor %}
        </select>
      </label>
      <label class="field"><span>Operational status *</span>
        <select name="ops_status" id="ops_status" required>
          {% for s in ops_statuses %}<option value="{{ s }}" {% if values.get('ops_status') == s %}selected{% endif %}>{{ s|human }}</option>{% endfor %}
        </select>
      </label>
    </div>
    <p class="hint">New ETA: <strong id="new_eta_preview">—</strong>. Filling either minutes or ETD updates the other.</p>
  </fieldset>

  <fieldset>
    <legend>Operations</legend>
    <div class="grid-2">
      <label class="field"><span>Gate change</span>
        <select name="new_gate_id">
          <option value="">No change ({{ flight.gate_code or 'none' }})</option>
          {% for g in gates %}<option value="{{ g.id }}" {% if values.get('new_gate_id') == g.id|string %}selected{% endif %}>{{ g.label }}</option>{% endfor %}
        </select>
      </label>
      <label class="field"><span>New boarding time</span>
        <input type="datetime-local" name="new_boarding_time" id="new_boarding_time" value="{{ values.get('new_boarding_time', '') }}">
      </label>
      <label class="field"><span>Aircraft swap</span>
        <select name="swap_aircraft_id">
          <option value="">No swap ({{ flight.registration }})</option>
          {% for a in aircraft if a.id != flight.aircraft_id %}<option value="{{ a.id }}" {% if values.get('swap_aircraft_id') == a.id|string %}selected{% endif %}>{{ a.label }}</option>{% endfor %}
        </select>
      </label>
      <label class="check"><input type="checkbox" name="pax_deboarded" {% if values.get('pax_deboarded') %}checked{% endif %}> Passengers deboarded</label>
    </div>
  </fieldset>

  <fieldset>
    <legend>Passengers</legend>
    <label class="field"><span>Public announcement</span>
      <textarea name="announcement" id="announcement" rows="3" maxlength="500">{{ values.get('announcement', '') }}</textarea>
    </label>
    <div class="checks">
      <label class="check"><input type="checkbox" name="meal_voucher" id="meal_voucher" {% if values.get('meal_voucher') %}checked{% endif %}> Meal voucher (auto ≥ 2 h)</label>
      <label class="check"><input type="checkbox" name="compensation_eligible" id="compensation_eligible" {% if values.get('compensation_eligible') %}checked{% endif %}> Compensation eligible (auto ≥ 3 h)</label>
      <label class="check"><input type="checkbox" name="rebooking_offered" id="rebooking_offered" {% if values.get('rebooking_offered') %}checked{% endif %}> Free rebooking offered</label>
    </div>
  </fieldset>

  <fieldset>
    <legend>Audit</legend>
    <div class="grid-2">
      <label class="field"><span>Reported by *</span>
        <input type="text" name="reported_by" maxlength="80" required value="{{ values.get('reported_by', '') }}" placeholder="e.g. R. Mehta (Duty Manager DEL)">
      </label>
      <label class="field"><span>Internal remarks</span>
        <input type="text" name="remarks" maxlength="500" value="{{ values.get('remarks', '') }}">
      </label>
    </div>
  </fieldset>

  <button type="submit" class="btn">File delay and cascade</button>
</form>

<script>
(() => {
  const form = document.getElementById("delay-form");
  const base = new Date(form.dataset.etd);
  const boarding = form.dataset.boarding ? new Date(form.dataset.boarding) : null;
  const blockMs = new Date("{{ flight.eta.strftime('%Y-%m-%dT%H:%M') }}") - base;
  const $ = (id) => document.getElementById(id);
  const pad = (n) => String(n).padStart(2, "0");
  const local = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  const hhmm = (d) => `${pad(d.getHours())}:${pad(d.getMinutes())}`;
  let announcementEdited = $("announcement").value.trim() !== "";
  $("announcement").addEventListener("input", () => { announcementEdited = true; });

  function sync(minutes) {
    const etd = new Date(base.getTime() + minutes * 60000);
    const eta = new Date(etd.getTime() + blockMs);
    $("new_eta_preview").textContent =
      eta.toLocaleDateString("en-GB", { weekday: "short", day: "2-digit", month: "short" }) + ", " + hhmm(eta);
    if (boarding) $("new_boarding_time").value = local(new Date(boarding.getTime() + minutes * 60000));
    $("meal_voucher").checked = minutes >= 120;
    $("compensation_eligible").checked = minutes >= 180;
    if (!announcementEdited) {
      const status = $("ops_status").value;
      $("announcement").value = status === "CANCELLED"
        ? `We regret to announce that flight ${form.dataset.flight} to ${form.dataset.dest} has been cancelled. Please contact the transfer desk for rebooking.`
        : status === "ON_HOLD"
        ? `Flight ${form.dataset.flight} to ${form.dataset.dest} is on hold. A new departure time will be announced shortly.`
        : `Flight ${form.dataset.flight} to ${form.dataset.dest} is delayed by ${minutes} minutes. New departure time ${hhmm(etd)}. We regret the inconvenience.`;
    }
  }
  $("minutes").addEventListener("input", (e) => {
    const m = parseInt(e.target.value || "0", 10);
    $("new_etd").value = m ? local(new Date(base.getTime() + m * 60000)) : "";
    sync(m);
  });
  $("new_etd").addEventListener("input", (e) => {
    if (!e.target.value) return;
    const m = Math.round((new Date(e.target.value) - base) / 60000);
    $("minutes").value = m;
    sync(m);
  });
  $("ops_status").addEventListener("change", () => sync(parseInt($("minutes").value || "0", 10)));
})();
</script>
{% endblock %}
````

### A.77 `templates/delays/list.html`

````html
{% extends "base.html" %}
{% from "_macros.html" import headline %}
{% block title %}Delay log{% endblock %}
{% block content %}
{% call headline('Delay log', '{:,}'.format(delays|length) ~ (' notice' if delays|length == 1 else ' notices') ~ (' still open' if open_only else ' filed'),
                  'Every delay filed, with how many other flights it moved. Open one to see its full impact across the network.') %}
  <a class="btn btn-ghost" href="{{ url_for('delays.list_view', open='0' if open_only else '1') }}">{{ 'Show all' if open_only else 'Open only' }}</a>
  <a class="btn btn-danger" href="{{ url_for('delays.reset') }}">Reset all delays</a>
{% endcall %}
<table class="data-table">
  <thead><tr><th>#</th><th>Flight</th><th>Route</th><th>Scheduled</th><th>Reason</th><th>Minutes</th><th>Status</th><th>Knock-on</th><th>Reported</th><th></th></tr></thead>
  <tbody>
    {% for d in delays %}
    <tr>
      <td>{{ d.delay_id }}</td>
      <td><a href="{{ url_for('flights.detail', flight_id=d.flight_id) }}">{{ d.flight_number }}</a></td>
      <td>{{ d.origin }} → {{ d.dest }}</td>
      <td>{{ d.std|when }}</td>
      <td>{{ d.category|human }}{% if d.iata_code %} ({{ d.iata_code }}){% endif %}</td>
      <td>{{ d.minutes }}</td>
      <td>{{ d.ops_status|human }}{% if d.resolved_at %}, resolved{% endif %}</td>
      <td>{{ d.knock_on_flights }} flights / {{ d.knock_on_minutes }} min</td>
      <td>{{ d.reported_by or '—' }}<br><span class="muted">{{ d.recorded_at|when }}</span></td>
      <td><a class="btn btn-small" href="{{ url_for('delays.detail', delay_id=d.delay_id) }}">Impact</a></td>
    </tr>
    {% else %}
    <tr><td colspan="10">No delays filed.</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
````

### A.78 `templates/delays/reset.html`

````html
{% extends "base.html" %}
{% block title %}Reset all delays{% endblock %}
{% block content %}
<h1>Reset all delays?</h1>
<p>This deletes all {{ count }} delay notices and their knock-on records, and puts every flight back on its scheduled times. Cancelled flights go back to SCHEDULED.</p>
<p class="hint">Gate changes and aircraft swaps made by notices are kept. Run <code>bash scripts/setup_db.sh</code> for a full rebuild.</p>
<form method="post" class="form-inline">
  <button type="submit" class="btn">Reset all delays</button>
  <a class="btn btn-ghost" href="{{ url_for('delays.list_view') }}">Cancel</a>
</form>
{% endblock %}
````

### A.79 `templates/error.html`

````html
{% extends "base.html" %}
{% block title %}{{ title }}{% endblock %}
{% block content %}
<header class="headline-block">
  <h1>{{ title }}</h1>
  <div>
    <span class="label">{{ 'MySQL error ' ~ code if code != 404 else 'Error 404' }}</span>
    <p>{{ message }}</p>
    {% if code != 404 %}
    <p class="hint">If a table was altered by hand (a column dropped or renamed), this page still expects the old structure.
      Check the table on the Schema page, or rebuild the database with <code>bash scripts/setup_db.sh</code>.</p>
    {% endif %}
    <div class="actions">
      <a class="btn" href="{{ url_for('dashboard.index') }}">Back to dashboard</a>
      <a class="btn btn-ghost" href="{{ url_for('schema.index') }}">Open schema</a>
    </div>
  </div>
</header>
{% endblock %}
````

### A.80 `templates/flights/detail.html`

````html
{% extends "base.html" %}
{% from "_macros.html" import all_columns %}
{% from "_status.html" import status_badge %}
{% block title %}Flight {{ flight.flight_number }}{% endblock %}
{% block content %}
<div class="page-header">
  <h1>{{ flight.flight_number }} — {{ flight.origin }} → {{ flight.dest }}</h1>
  <div class="actions">
    {% if flight.status in ('SCHEDULED', 'BOARDING', 'DEPARTED') %}
    <a class="btn btn-primary-warn" href="{{ url_for('flights.delay', flight_id=flight.flight_id) }}">Delay this flight</a>
    {% endif %}
    <a class="btn btn-ghost" href="{{ url_for('flights.edit', flight_id=flight.flight_id) }}">Edit</a>
    <a class="btn btn-ghost" href="{{ url_for('cascade.trace', flight_id=flight.flight_id) }}">Cascade trace</a>
    <a class="btn btn-ghost" href="{{ url_for('crew.replacement', flight_id=flight.flight_id) }}">Replacement crew</a>
    <form method="post" action="{{ url_for('flights.delete', flight_id=flight.flight_id) }}" onsubmit="return confirm('Delete this flight?');" class="inline-form">
      <button type="submit" class="btn btn-danger">Delete</button>
    </form>
  </div>
</div>

<dl class="detail-grid">
  <dt>Route</dt><dd>{{ flight.origin_city }} ({{ flight.origin }}) → {{ flight.dest_city }} ({{ flight.dest }})</dd>
  <dt>Aircraft</dt><dd>{{ flight.registration }}</dd>
  <dt>Gate</dt><dd>{{ flight.gate_code or '—' }}</dd>
  <dt>Status</dt><dd>{{ status_badge(flight.display_status) }}</dd>
  <dt>Scheduled departure / arrival</dt><dd>{{ flight.std|when }} / {{ flight.sta|when }}</dd>
  <dt>Estimated departure / arrival</dt><dd>{% if flight.delay_minutes %}<strong class="late">{{ flight.etd|when }} / {{ flight.eta|when }}</strong>{% else %}On time{% endif %}</dd>
  <dt>Boarding / gate close</dt><dd>{{ (flight.boarding_start|when) or '—' }} / {{ (flight.gate_close|when) or '—' }}</dd>
  <dt>Actual departure / arrival</dt><dd>{{ (flight.actual_departure|when) or '—' }} / {{ (flight.actual_arrival|when) or '—' }}</dd>
  <dt>Total delay</dt><dd>{{ flight.delay_minutes }} min</dd>
  <dt>Knock-on source</dt><dd>{% if flight.parent_flight_id %}<a href="{{ url_for('flights.detail', flight_id=flight.parent_flight_id) }}">flight #{{ flight.parent_flight_id }}</a>{% else %}—{% endif %}</dd>
  <dt>Remarks</dt><dd>{{ flight.remarks or '—' }}</dd>
</dl>

<h2>Crew assigned</h2>
<table class="data-table">
  <thead><tr><th>Name</th><th>Role</th><th>Assigned</th><th></th></tr></thead>
  <tbody>
    {% for c in crew %}
    <tr>
      <td>{{ c.name }}</td>
      <td>{{ c.role|human }}</td>
      <td>{{ c.assigned_at|when }}</td>
      <td>
        <form method="post" action="{{ url_for('flights.unassign_crew', flight_id=flight.flight_id, crew_id=c.crew_id) }}" class="inline-form">
          <button type="submit" class="btn btn-small">Unassign</button>
        </form>
      </td>
    </tr>
    {% else %}
    <tr><td colspan="4">No crew assigned.</td></tr>
    {% endfor %}
  </tbody>
</table>

<form method="post" action="{{ url_for('flights.assign_crew', flight_id=flight.flight_id) }}" class="form-inline">
  <select name="crew_id" required aria-label="Crew member">
    {% for c in all_crew %}
    <option value="{{ c.id }}">{{ c.label }}</option>
    {% endfor %}
  </select>
  <select name="role" required aria-label="Role on this flight">
    {% for r in enum_values('crew', 'role') %}<option value="{{ r }}">{{ r|human }}</option>{% endfor %}
  </select>
  <button type="submit" class="btn btn-ghost">Assign crew</button>
</form>

<h2>Delays filed on this flight</h2>
<table class="data-table">
  <thead><tr><th>#</th><th>Reason</th><th>Details</th><th>Minutes</th><th>Status</th><th>Reported</th><th></th></tr></thead>
  <tbody>
    {% for d in delays %}
    <tr>
      <td>{{ d.delay_id }}</td>
      <td>{{ d.category|human }}{% if d.iata_code %}, {{ d.iata_code }} {{ d.description }}{% endif %}</td>
      <td>{{ d.sub_reason or '—' }}</td>
      <td>{{ d.minutes }}</td>
      <td>{{ d.ops_status|human }}{% if d.resolved_at %}, resolved{% endif %}</td>
      <td>{{ d.reported_by or '—' }}<br><span class="muted">{{ d.recorded_at|when }}</span></td>
      <td><a class="btn btn-small" href="{{ url_for('delays.detail', delay_id=d.delay_id) }}">Impact</a></td>
    </tr>
    {% else %}
    <tr><td colspan="7">No delays filed on this flight.</td></tr>
    {% endfor %}
  </tbody>
</table>

<h2>Knock-on delay received from other flights</h2>
<table class="data-table">
  <thead><tr><th>Notice</th><th>Started at</th><th>Link</th><th>Caused by</th><th>ETD before → after</th><th>Added</th></tr></thead>
  <tbody>
    {% for k in knock_on %}
    <tr>
      <td><a href="{{ url_for('delays.detail', delay_id=k.delay_id) }}">#{{ k.delay_id }}</a></td>
      <td>{{ k.source_flight }}</td>
      <td><span class="badge badge-link-{{ k.link|lower }}">{{ k.link }}</span></td>
      <td>{% if k.cause_flight_id %}<a href="{{ url_for('flights.detail', flight_id=k.cause_flight_id) }}">{{ k.cause_flight }}</a>{% else %}runway slots{% endif %}</td>
      <td>{{ k.old_etd|when }} → <span class="late">{{ k.new_etd|when }}</span></td>
      <td>+{{ k.minutes_added }} min</td>
    </tr>
    {% else %}
    <tr><td colspan="6">None.</td></tr>
    {% endfor %}
  </tbody>
</table>

{{ all_columns('flight', record) }}
{% endblock %}
````

### A.81 `templates/flights/form.html`

````html
{% extends "base.html" %}
{% from "_macros.html" import field %}
{% block title %}{{ 'Edit' if flight else 'New' }} Flight{% endblock %}
{% block content %}
<h1>{{ 'Edit' if flight else 'New' }} Flight</h1>
<form method="post" class="form">
  {{ field('flight_number', 'Flight Number', flight.flight_number if flight else '', required=True) }}
  {{ field('route_id', 'Route', flight.route_id if flight else '', type='fk', options=routes, required=True) }}
  {{ field('aircraft_id', 'Aircraft', flight.aircraft_id if flight else '', type='fk', options=aircraft, required=True) }}
  {{ field('sched_departure', 'Scheduled Departure', (flight.sched_departure|string)[:16] if flight and flight.sched_departure else '', type='datetime-local', required=True) }}
  {{ field('sched_arrival', 'Scheduled Arrival', (flight.sched_arrival|string)[:16] if flight and flight.sched_arrival else '', type='datetime-local', required=True) }}
  {{ field('boarding_start', 'Boarding Start', (flight.boarding_start|string)[:16] if flight and flight.boarding_start else '', type='datetime-local') }}
  {{ field('gate_close', 'Gate Close', (flight.gate_close|string)[:16] if flight and flight.gate_close else '', type='datetime-local') }}
  {% if flight %}
  {{ field('actual_departure', 'Actual Departure', (flight.actual_departure|string)[:16] if flight.actual_departure else '', type='datetime-local') }}
  {{ field('actual_arrival', 'Actual Arrival', (flight.actual_arrival|string)[:16] if flight.actual_arrival else '', type='datetime-local') }}
  {% endif %}
  {{ field('gate_id', 'Departure Gate', flight.gate_id if flight else '', type='fk', options=gates) }}
  {{ field('remarks', 'Remarks', flight.remarks if flight else '') }}
  {{ field('status', 'Status', flight.status if flight else 'SCHEDULED', type='select', options=enum_values('flight', 'status'), required=True) }}
  <button type="submit" class="btn">Save</button>
</form>
{% endblock %}
````

### A.82 `templates/flights/list.html`

````html
{% extends "base.html" %}
{% from "_macros.html" import headline %}
{% from "_status.html" import status_badge, times %}
{% block title %}Flights{% endblock %}
{% block content %}
{% call headline('Flights', '{:,}'.format(flights|length) ~ (' flight' if flights|length == 1 else ' flights') ~ ' shown',
                  'Every scheduled leg across the network, with its scheduled and estimated times. Press Delay on any upcoming flight to file one.') %}
  <a class="btn" href="{{ url_for('flights.new') }}">New flight</a>
{% endcall %}

<form method="get" class="filter-bar">
  <input type="search" name="q" value="{{ q or '' }}" placeholder="Flight no., airport (DEL) or aircraft">
  <select name="status">
    <option value="">All statuses</option>
    {% for s in ['DELAYED'] + enum_values('flight', 'status') %}
    <option value="{{ s }}" {% if status == s %}selected{% endif %}>{{ s|human }}</option>
    {% endfor %}
  </select>
  <input type="date" name="date" value="{{ date or '' }}">
  <button type="submit" class="btn btn-ghost">Filter</button>
  {% if q or status or date %}<a class="btn btn-ghost" href="{{ url_for('flights.list_view') }}">Clear</a>{% endif %}
</form>

<table class="data-table">
  <thead><tr><th>Flight</th><th>Route</th><th>Aircraft</th><th>Date</th><th>Dep</th><th>Arr</th><th>Gate</th><th>Status</th><th>Delay</th><th></th></tr></thead>
  <tbody>
    {% for f in flights %}
    <tr class="{% if f.display_status == 'DELAYED' %}row-delayed{% endif %}">
      <td><a href="{{ url_for('flights.detail', flight_id=f.flight_id) }}">{{ f.flight_number }}</a></td>
      <td>{{ f.origin }} → {{ f.dest }}</td>
      <td>{{ f.registration }}</td>
      <td class="nowrap">{{ f.std.strftime('%a %d %b') }}</td>
      <td>{{ times(f.std, f.etd, f.delay_minutes) }}</td>
      <td>{{ times(f.sta, f.eta, f.delay_minutes) }}</td>
      <td>{{ f.gate_code or '—' }}</td>
      <td>{{ status_badge(f.display_status) }}</td>
      <td>{% if f.delay_minutes %}{{ f.delay_minutes }} min{% else %}—{% endif %}</td>
      <td>{% if f.status in ('SCHEDULED', 'BOARDING', 'DEPARTED') %}<a class="btn btn-small btn-warn" href="{{ url_for('flights.delay', flight_id=f.flight_id) }}">Delay</a>{% endif %}</td>
    </tr>
    {% else %}
    <tr><td colspan="10">No flights found.</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
````

### A.83 `templates/passengers/detail.html`

````html
{% extends "base.html" %}
{% from "_macros.html" import all_columns %}
{% block title %}{{ passenger.name }}{% endblock %}
{% block content %}
<div class="page-header">
  <h1>{{ passenger.name }}</h1>
  <div class="actions">
    <a class="btn btn-ghost" href="{{ url_for('passengers.edit', passenger_id=passenger.passenger_id) }}">Edit</a>
    <form method="post" action="{{ url_for('passengers.delete', passenger_id=passenger.passenger_id) }}" onsubmit="return confirm('Delete this passenger?');" class="inline-form">
      <button type="submit" class="btn btn-danger">Delete</button>
    </form>
  </div>
</div>
<dl class="detail-grid">
  <dt>Passport</dt><dd>{{ passenger.passport_no or '—' }}</dd>
  <dt>Email</dt><dd>{{ passenger.email or '—' }}</dd>
  <dt>Phone</dt><dd>{{ passenger.phone or '—' }}</dd>
  <dt>Date of birth</dt><dd>{{ passenger.date_of_birth|when }}</dd>
</dl>

<h2>Bookings</h2>
<table class="data-table">
  <thead><tr><th>PNR</th><th>Date</th><th>Status</th></tr></thead>
  <tbody>
    {% for b in bookings %}
    <tr>
      <td><a href="{{ url_for('bookings.detail', booking_id=b.booking_id) }}">{{ b.pnr }}</a></td>
      <td>{{ b.booking_date|when }}</td>
      <td>{{ b.status|human }}</td>
    </tr>
    {% else %}
    <tr><td colspan="3">No bookings.</td></tr>
    {% endfor %}
  </tbody>
</table>

{{ all_columns('passenger', record) }}
{% endblock %}
````

### A.84 `templates/passengers/form.html`

````html
{% extends "base.html" %}
{% from "_macros.html" import field %}
{% block title %}{{ 'Edit' if passenger else 'New' }} Passenger{% endblock %}
{% block content %}
<h1>{{ 'Edit' if passenger else 'New' }} Passenger</h1>
<form method="post" class="form">
  {{ field('name', 'Name', passenger.name if passenger else '', required=True) }}
  {{ field('passport_no', 'Passport No.', passenger.passport_no if passenger else '') }}
  {{ field('email', 'Email', passenger.email if passenger else '', type='email') }}
  {{ field('phone', 'Phone', passenger.phone if passenger else '') }}
  {{ field('date_of_birth', 'Date of Birth', passenger.date_of_birth if passenger else '', type='date', required=True) }}
  <button type="submit" class="btn">Save</button>
</form>
{% endblock %}
````

### A.85 `templates/passengers/list.html`

````html
{% extends "base.html" %}
{% from "_macros.html" import headline %}
{% block title %}Passengers{% endblock %}
{% block content %}
{% call headline('Passengers', '{:,}'.format(passengers|length) ~ ' passengers', 'Everyone holding a booking. Open a passenger to see their bookings and connections.') %}
  <a class="btn" href="{{ url_for('passengers.new') }}">New passenger</a>
{% endcall %}
<form method="get" class="filter-bar">
  <input type="text" name="q" placeholder="Search by name" value="{{ search or '' }}">
  <button type="submit" class="btn btn-ghost">Search</button>
</form>
<table class="data-table">
  <thead><tr><th>Name</th><th>Passport</th><th>Email</th><th>Phone</th></tr></thead>
  <tbody>
    {% for p in passengers %}
    <tr>
      <td><a href="{{ url_for('passengers.detail', passenger_id=p.passenger_id) }}">{{ p.name }}</a></td>
      <td>{{ p.passport_no or '—' }}</td>
      <td>{{ p.email or '—' }}</td>
      <td>{{ p.phone or '—' }}</td>
    </tr>
    {% else %}
    <tr><td colspan="4">No passengers found.</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
````

### A.86 `templates/reports/delay_causes.html`

````html
{% extends "base.html" %}
{% block title %}Top Delay Causes{% endblock %}
{% block content %}
<h1>Top Delay Causes</h1>
<table class="data-table">
  <thead><tr><th>Category</th><th>Count</th><th>Total Minutes</th><th>Avg Minutes</th></tr></thead>
  <tbody>
    {% for r in rows %}
    <tr><td>{{ r.category|human }}</td><td>{{ r.delay_count }}</td><td>{{ r.total_minutes }}</td><td>{{ r.avg_minutes }}</td></tr>
    {% else %}
    <tr><td colspan="4">No data.</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
````

### A.87 `templates/reports/duty_status.html`

````html
{% extends "base.html" %}
{% block title %}Crew Duty Status{% endblock %}
{% block content %}
<h1>Crew Duty Status</h1>
<table class="data-table">
  <thead><tr><th>Name</th><th>Role</th><th>Hours on duty</th><th>Hours flown</th><th>Remaining</th></tr></thead>
  <tbody>
    {% for r in rows %}
    <tr><td>{{ r.name }}</td><td>{{ r.role|human }}</td><td>{{ r.hours_on_duty }}</td><td>{{ r.hours_flown }}</td><td>{{ r.hours_remaining }}</td></tr>
    {% else %}
    <tr><td colspan="5">No crew near the duty limit today.</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
````

### A.88 `templates/reports/index.html`

````html
{% extends "base.html" %}
{% from "_macros.html" import headline %}
{% block title %}Reports{% endblock %}
{% block content %}
{{ headline('Reports', '5 reports', 'Performance across the whole operation, recalculated from the live data every time you open one.') }}
<ul class="link-list">
  <li><a href="{{ url_for('reports.ontime') }}"><span>On-time performance<small>Share of flights within 15 minutes of schedule, by day.</small></span></a></li>
  <li><a href="{{ url_for('reports.delay_causes') }}"><span>Delay causes<small>Filed delays and minutes lost, by category.</small></span></a></li>
  <li><a href="{{ url_for('reports.load_factor') }}"><span>Load factor<small>Seats sold against capacity, per flight.</small></span></a></li>
  <li><a href="{{ url_for('reports.duty_status') }}"><span>Crew duty status<small>Crew close to the 11-hour daily limit today.</small></span></a></li>
  <li><a href="{{ url_for('reports.utilisation') }}"><span>Aircraft utilisation<small>Flights, scheduled hours and delay hours per aircraft.</small></span></a></li>
</ul>
{% endblock %}
````

### A.89 `templates/reports/load_factor.html`

````html
{% extends "base.html" %}
{% block title %}Load Factor{% endblock %}
{% block content %}
<h1>Load Factor per Flight</h1>
<table class="data-table">
  <thead><tr><th>Flight</th><th>Departure</th><th>Seats</th><th>Sold</th><th>Load %</th></tr></thead>
  <tbody>
    {% for r in rows %}
    <tr><td>{{ r.flight_number }}</td><td>{{ r.sched_departure|when }}</td><td>{{ r.seat_capacity }}</td><td>{{ r.tickets_sold }}</td><td>{{ r.load_factor_pct }}%</td></tr>
    {% else %}
    <tr><td colspan="5">No data.</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
````

### A.90 `templates/reports/ontime.html`

````html
{% extends "base.html" %}
{% block title %}On-time Performance{% endblock %}
{% block content %}
<h1>On-time Performance</h1>
<table class="data-table">
  <thead><tr><th>Date</th><th>Total Flights</th><th>On-time</th><th>On-time %</th></tr></thead>
  <tbody>
    {% for r in rows %}
    <tr><td>{{ r.flight_date|when }}</td><td>{{ r.total_flights }}</td><td>{{ r.on_time_flights }}</td><td>{{ r.on_time_pct }}%</td></tr>
    {% else %}
    <tr><td colspan="4">No data.</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
````

### A.91 `templates/reports/utilisation.html`

````html
{% extends "base.html" %}
{% block title %}Aircraft Utilisation{% endblock %}
{% block content %}
<h1>Aircraft Utilisation</h1>
<table class="data-table">
  <thead><tr><th>Registration</th><th>Model</th><th>Flights</th><th>Sched Hours</th><th>Delay Hours</th></tr></thead>
  <tbody>
    {% for r in rows %}
    <tr><td>{{ r.registration }}</td><td>{{ r.model }}</td><td>{{ r.flights_operated }}</td><td>{{ r.scheduled_flight_hours }}</td><td>{{ r.total_delay_hours }}</td></tr>
    {% else %}
    <tr><td colspan="5">No data.</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
````

### A.92 `templates/schema/index.html`

````html
{% extends "base.html" %}
{% from "_macros.html" import headline %}
{% block title %}Schema{% endblock %}
{% block content %}
{{ headline('Database schema', '{:,}'.format(tables|length) ~ ' tables, ' ~ views|length ~ ' views',
            'Read live from information_schema: every table and view the application runs on.') }}
<table class="data-table">
  <thead><tr><th>Table</th><th>Rows</th><th>Created</th><th></th></tr></thead>
  <tbody>
    {% for t in tables %}
    <tr>
      <td><a href="{{ url_for('schema.table_detail', table_name=t.table_name) }}">{{ t.table_name }}</a></td>
      <td class="num">{{ t.table_rows }}</td>
      <td class="muted">{{ t.create_time|when }}</td>
      <td><a class="btn btn-small" href="{{ url_for('schema.rows', table_name=t.table_name) }}">Rows</a></td>
    </tr>
    {% endfor %}
  </tbody>
</table>

<h2>Views</h2>
<p class="hint">Derived on every read, never stored: estimated times and the operational flags.</p>
<table class="data-table">
  <thead><tr><th>View</th><th></th></tr></thead>
  <tbody>
    {% for v in views %}
    <tr><td><a href="{{ url_for('schema.table_detail', table_name=v.table_name) }}">{{ v.table_name }}</a></td>
        <td><a class="btn btn-small" href="{{ url_for('schema.rows', table_name=v.table_name) }}">Rows</a></td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
````

### A.93 `templates/schema/rows.html`

````html
{% extends "base.html" %}
{% block title %}{{ table_name }} rows{% endblock %}
{% block content %}
<div class="page-header">
  <div>
    <h1>{{ table_name }}</h1>
    <p>{{ '{:,}'.format(total) }} rows, {{ cols|length }} columns. Read live with <code>SELECT *</code>, so rows and columns changed directly in MySQL show up on refresh.</p>
  </div>
  <div class="actions">
    <a class="btn btn-ghost" href="{{ url_for('schema.table_detail', table_name=table_name) }}">Structure</a>
    <a class="btn btn-ghost" href="{{ url_for('schema.index') }}">All tables</a>
  </div>
</div>
<div class="table-scroll">
<table class="data-table">
  <thead><tr>{% for c in cols %}<th>{{ c }}</th>{% endfor %}</tr></thead>
  <tbody>
    {% for r in rows %}
    <tr>{% for c in cols %}<td class="nowrap">{% if r[c] is none %}<span class="muted">NULL</span>{% else %}{{ r[c] }}{% endif %}</td>{% endfor %}</tr>
    {% else %}
    <tr><td colspan="{{ cols|length or 1 }}">No rows.</td></tr>
    {% endfor %}
  </tbody>
</table>
</div>
{% if pages > 1 %}
<nav class="dots" aria-label="Pages">
  {% if page > 1 %}<a class="dot-link" href="{{ url_for('schema.rows', table_name=table_name, page=page - 1) }}">Previous</a>{% endif %}
  <span class="muted">Page {{ page }} of {{ pages }}</span>
  {% if page < pages %}<a class="dot-link" href="{{ url_for('schema.rows', table_name=table_name, page=page + 1) }}">Next</a>{% endif %}
</nav>
{% endif %}
{% endblock %}
````

### A.94 `templates/schema/table.html`

````html
{% extends "base.html" %}
{% block title %}{{ table_name }} — Schema{% endblock %}
{% block content %}
<h1>{{ table_name }}</h1>
<h2>Columns</h2>
<table class="data-table">
  <thead><tr><th>Column</th><th>Type</th><th>Nullable</th><th>Key</th><th>Default</th><th>Extra</th></tr></thead>
  <tbody>
    {% for c in columns %}
    <tr>
      <td>{{ c.column_name }}</td>
      <td>{{ c.column_type }}</td>
      <td>{{ c.is_nullable }}</td>
      <td>{{ c.column_key }}</td>
      <td>{{ c.column_default if c.column_default is not none else '—' }}</td>
      <td>{{ c.extra }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>

<h2>Foreign Keys</h2>
<table class="data-table">
  <thead><tr><th>Column</th><th>References</th></tr></thead>
  <tbody>
    {% for fk in foreign_keys %}
    <tr><td>{{ fk.column_name }}</td><td>{{ fk.referenced_table_name }}.{{ fk.referenced_column_name }}</td></tr>
    {% else %}
    <tr><td colspan="2">No foreign keys.</td></tr>
    {% endfor %}
  </tbody>
</table>
<div class="actions">
  <a class="btn btn-ghost" href="{{ url_for('schema.rows', table_name=table_name) }}">See every row</a>
  <a class="btn btn-ghost" href="{{ url_for('schema.index') }}">All tables</a>
</div>
{% endblock %}
````

### A.95 `static/css/style.css`

````css
/* Airline Cascades — built on the Refero "Dala" style reference (DESIGN.md).
   The first :root block is the reference's CSS Custom Properties, verbatim.
   Everything after it uses those tokens; the few app-only tokens (status
   colours, hairlines) are declared separately under "App extensions". */

:root {
  /* Colors */
  --color-void: #000000;
  --color-bone-white: #ffffff;
  --color-ash-gray: #9a9a9a;
  --color-silver-mist: #bdbdbd;
  --color-electric-iris: #8052ff;
  --color-saffron-spark: #ffb829;
  --color-deep-verdant: #15846e;

  /* Typography — Font Families */
  --font-ppneuemontreal: 'PPNeueMontreal', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;

  /* Typography — Scale */
  --text-caption: 12px;
  --leading-caption: 1.5;
  --text-nav-label: 14px;
  --leading-nav-label: 1.2;
  --tracking-nav-label: 0.35px;
  --text-body: 18px;
  --leading-body: 1.5;
  --text-heading-2xs: 24px;
  --leading-heading-2xs: 1.25;
  --tracking-heading-2xs: -0.48px;
  --text-heading-xs: 27px;
  --leading-heading-xs: 1;
  --text-subheading: 36px;
  --leading-subheading: 1.2;
  --text-heading-sm: 42px;
  --leading-heading-sm: 1.2;
  --tracking-heading-sm: -1.68px;
  --text-heading: 48px;
  --leading-heading: 1.1;
  --tracking-heading: -1.68px;
  --text-heading-lg: 78px;
  --leading-heading-lg: 1.1;
  --tracking-heading-lg: -3.12px;
  --text-display: 113px;
  --leading-display: 1.1;
  --tracking-display: -4.52px;

  /* Typography — Weights */
  --font-weight-extralight: 200;
  --font-weight-regular: 400;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;

  /* Spacing */
  --spacing-unit: 6px;
  --spacing-6: 6px;
  --spacing-12: 12px;
  --spacing-18: 18px;
  --spacing-24: 24px;
  --spacing-30: 30px;
  --spacing-36: 36px;
  --spacing-60: 60px;
  --spacing-96: 96px;
  --spacing-120: 120px;

  /* Layout */
  --page-max-width: 1280px;
  --section-gap: 60-120px;
  --card-padding: 24-38px;
  --element-gap: 6-18px;

  /* Border Radius */
  --radius-3xl: 24px;
  --radius-full: 9999px;

  /* Named Radii */
  --radius-nav: 24px;
  --radius-tags: 9999px;
  --radius-cards: 24px;
  --radius-buttons: 24px;

  /* Surfaces */
  --surface-void-canvas: #000000;
  --surface-deep-verdant-tint: #15846;
  --surface-electric-iris: #8052ff;
}

/* ---------- App extensions (not in the reference) ----------
   The reference's range tokens (--section-gap: 60-120px etc.) and the
   truncated #15846 are kept verbatim above but aren't valid CSS values, so
   nothing reads them; spacing uses the --spacing-* scale instead.
   PPNeueMontreal is a paid face; the reference names Inter as its substitute. */
:root {
  color-scheme: dark;
  --font-app: 'PPNeueMontreal', 'Inter', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --tracking-display-em: -0.04em;          /* "-0.04em on all display sizes 42px and above" */
  --tracking-nav-em: 0.025em;
  --color-iris-text: #a386ff;              /* iris lifted for small text on black (contrast) */
  --color-verdant-text: #3ecfae;           /* deep verdant lifted: "on time" */
  --color-magenta: #ff5fa2;                /* from the particle spectrum: cancelled / destructive */
  --color-blue: #5aa9ff;                   /* from the particle spectrum: boarding / gate link */
  --line-hairline: rgba(255, 255, 255, 0.08);
  --line-field: rgba(255, 255, 255, 0.22);
}

* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }

body {
  margin: 0;
  background: var(--surface-void-canvas);
  color: var(--color-bone-white);
  font-family: var(--font-app);
  font-feature-settings: "ss01" on;
  font-size: 15px;                          /* 15px body at weight 400 (reference) */
  font-weight: var(--font-weight-regular);
  line-height: var(--leading-body);
  -webkit-font-smoothing: antialiased;
}

a { color: var(--color-bone-white); text-decoration-color: rgba(255, 255, 255, 0.3); text-underline-offset: 3px; }
a:hover { color: var(--color-saffron-spark); text-decoration-color: currentColor; }
:focus-visible { outline: 2px solid var(--color-electric-iris); outline-offset: 3px; border-radius: 6px; }
code { font-family: inherit; color: var(--color-saffron-spark); }

/* Ambient Particle Field: fixed behind every page. */
#ambient-field { position: fixed; inset: 0; width: 100%; height: 100%; z-index: -1; pointer-events: none; }

/* ---------- type: scale, not weight, carries hierarchy ---------- */

h1, h2, h3 { font-weight: var(--font-weight-regular); margin: 0; }
h1 {
  font-size: clamp(44px, 6vw, var(--text-heading-lg));
  line-height: var(--leading-heading-lg);
  letter-spacing: var(--tracking-display-em);
  max-width: 16ch;
}
h2 {
  font-size: clamp(30px, 3.4vw, var(--text-heading-sm));
  line-height: var(--leading-heading-sm);
  letter-spacing: var(--tracking-display-em);
  margin: var(--spacing-96) 0 var(--spacing-30);
}
h1 + h2 { margin-top: var(--spacing-60); }

p {
  font-size: var(--text-body);
  line-height: var(--leading-body);
  font-weight: var(--font-weight-extralight);
  color: var(--color-silver-mist);
  max-width: 520px;
}

.muted { color: var(--color-ash-gray); }
.late { color: var(--color-saffron-spark); }
strong.late { font-weight: var(--font-weight-regular); }
.nowrap { white-space: nowrap; }
.hint {
  color: var(--color-ash-gray);
  font-size: 14px; line-height: var(--leading-body);
  font-weight: var(--font-weight-regular);
  max-width: 80ch;
}
/* Section label: 14px / 600 / amber / 0.35px (Section Headline Block) */
.label {
  display: block;
  font-size: var(--text-nav-label); line-height: var(--leading-nav-label);
  font-weight: var(--font-weight-semibold); letter-spacing: var(--tracking-nav-label);
  text-transform: uppercase; color: var(--color-saffron-spark);
}
.time, .num { font-variant-numeric: tabular-nums; }

/* ---------- Navigation Bar: transparent, logo left, links right, one violet pill ---------- */

.topbar {
  display: flex; align-items: center; justify-content: space-between; gap: var(--spacing-24);
  max-width: var(--page-max-width); margin: 0 auto;
  padding: var(--spacing-24) var(--spacing-36);
}
.topbar .brand { flex: none; }
.brand {
  display: flex; align-items: center; gap: var(--spacing-12);
  text-decoration: none; color: var(--color-bone-white);
  font-size: 17px; font-weight: var(--font-weight-regular);
  white-space: nowrap;
}
.brand:hover { color: var(--color-bone-white); }
.brand svg { width: 24px; height: 24px; }
.topbar nav { display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: var(--spacing-6) var(--spacing-18); flex: 1; }
.topbar nav a:not(.btn), .topbar-end .nav-late {
  font-size: 12px; line-height: var(--leading-nav-label);
  font-weight: var(--font-weight-semibold); letter-spacing: var(--tracking-nav-em);
  text-transform: uppercase; text-decoration: none;
  color: var(--color-ash-gray); padding: var(--spacing-6) 0;
}
.topbar nav a:not(.btn):hover, .topbar nav a[aria-current="page"] { color: var(--color-bone-white); }
.topbar-end { display: flex; align-items: center; gap: var(--spacing-18); flex: none; }
.topbar-end .nav-late { color: var(--color-saffron-spark); white-space: nowrap; }

.container { max-width: var(--page-max-width); margin: 0 auto; padding: var(--spacing-36) var(--spacing-36) var(--spacing-120); }

/* ---------- page headers ---------- */

.page-header {
  display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap;
  gap: var(--spacing-24) var(--spacing-36);
  margin-bottom: var(--spacing-60);
}
.page-header h1, .page-header h2 { margin: 0; }
.page-header p { margin: var(--spacing-12) 0 0; }
.actions { display: flex; flex-wrap: wrap; align-items: center; gap: var(--spacing-12) var(--spacing-24); }
h1 + p, h1 + .hint { margin-top: var(--spacing-18); }
h1 + .form, h1 + form, h1 + table, h1 + .data-table { margin-top: var(--spacing-36); }

/* Section Headline Block: oversized headline left; amber label, light body and action right */
.headline-block {
  display: grid;
  grid-template-columns: minmax(0, 7fr) minmax(0, 5fr);
  gap: var(--spacing-36) var(--spacing-60);
  align-items: end;
  margin: var(--spacing-24) 0 var(--spacing-96);
}
.headline-block h1 { max-width: 12ch; }
.headline-block .label { margin-bottom: var(--spacing-12); }
.headline-block p { margin: 0 0 var(--spacing-24); color: var(--color-bone-white); }
.headline-block p:last-child { margin-bottom: 0; }

/* ---------- Primary Action Button: the violet pill ---------- */

.btn {
  display: inline-flex; align-items: center; justify-content: center; gap: var(--spacing-6);
  padding: 14.4px 15.96px;
  border: 0;
  border-radius: var(--radius-buttons);
  background: var(--color-electric-iris);
  color: var(--color-bone-white);
  font: var(--font-weight-semibold) var(--text-nav-label)/1.2 var(--font-app);
  letter-spacing: var(--tracking-nav-em);
  text-transform: uppercase;
  text-decoration: none;
  cursor: pointer;
  white-space: nowrap;
  transition: background-color 0.15s ease;
}
.btn:hover { background: #9270ff; color: var(--color-bone-white); }
.btn:active { background: #6f40f0; }

/* ---------- Ghost Text Button: no background, no border, 14px / 400 ---------- */

.btn-ghost, .btn-small, .btn-danger, .btn-warn {
  padding: var(--spacing-6) 0;
  background: none;
  border-radius: 0;
  color: var(--color-ash-gray);
  font-weight: var(--font-weight-regular);
  text-transform: none;
  letter-spacing: 0;
}
.btn-ghost:hover, .btn-small:hover { background: none; color: var(--color-bone-white); }
.btn-danger { color: var(--color-magenta); }
.btn-danger:hover { background: none; color: #ff8cbe; }
.btn-warn { color: var(--color-bone-white); }
.btn-warn::before,
.btn.btn-primary-warn::before {
  content: ""; width: 8px; height: 8px; background: var(--color-saffron-spark);
  clip-path: polygon(50% 0, 100% 100%, 0 100%);
}
.btn-warn:hover { background: none; color: var(--color-saffron-spark); }

.inline-form { display: inline; margin: 0; }

/* ---------- flashes ---------- */

.flashes { list-style: none; padding: 0; margin: 0 0 var(--spacing-36); display: grid; gap: var(--spacing-6); }
.flash { display: flex; align-items: baseline; gap: var(--spacing-12); font-size: var(--text-body); font-weight: var(--font-weight-extralight); }
.flash::before {
  content: ""; flex: none; width: 10px; height: 10px; transform: translateY(1px);
  clip-path: polygon(50% 0, 100% 100%, 0 100%);
}
.flash-success::before { background: var(--color-verdant-text); }
.flash-error { color: #ffc2dc; }
.flash-error::before { background: var(--color-magenta); }

/* ---------- figures ---------- */

.stat-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(132px, 1fr));
  gap: var(--spacing-36) var(--spacing-30);
  margin: 0 0 var(--spacing-24);
}
.stat-card { display: flex; flex-direction: column; gap: var(--spacing-6); }
.stat-value {
  font-size: clamp(34px, 3.6vw, var(--text-heading)); line-height: 1;
  letter-spacing: var(--tracking-display-em); font-variant-numeric: tabular-nums;
}
.stat-label { color: var(--color-ash-gray); font-size: 14px; font-weight: var(--font-weight-extralight); }

/* ---------- tables ---------- */

.data-table { width: 100%; border-collapse: collapse; margin: 0 0 var(--spacing-24); }
.data-table th {
  text-align: left; padding: 0 var(--spacing-18) var(--spacing-12) 0;
  font-size: var(--text-caption); line-height: var(--leading-caption);
  font-weight: var(--font-weight-semibold); letter-spacing: var(--tracking-nav-label);
  text-transform: uppercase; color: var(--color-ash-gray);
  border-bottom: 1px solid var(--line-field);
  white-space: nowrap;
}
.data-table td {
  padding: var(--spacing-12) var(--spacing-18) var(--spacing-12) 0;
  border-bottom: 1px solid var(--line-hairline);
  font-size: 15px; font-weight: var(--font-weight-regular);
  vertical-align: top;
}
.data-table th:last-child, .data-table td:last-child { padding-right: 0; }
.data-table tbody tr:hover td { background: rgba(128, 82, 255, 0.07); }
.data-table td a { text-decoration: none; }
.data-table td a:hover { color: var(--color-saffron-spark); }
.data-table td[colspan] { color: var(--color-ash-gray); padding: var(--spacing-24) 0; }
.data-table .btn-small, .data-table .btn-warn, .data-table .btn-danger { padding: 0; }
.data-table td:last-child .btn-small, .data-table td:last-child .btn-warn { margin-left: var(--spacing-12); }
.data-table td:last-child > :first-child { margin-left: 0; }
.row-delayed td:first-child { box-shadow: inset 2px 0 0 var(--color-saffron-spark); padding-left: var(--spacing-12); }

/* ---------- status marks: triangle glyph + text ---------- */

.badge {
  display: inline-flex; align-items: center; gap: 7px;
  font-size: var(--text-caption); font-weight: var(--font-weight-semibold);
  letter-spacing: var(--tracking-nav-label); text-transform: uppercase;
  color: var(--color-silver-mist); white-space: nowrap;
}
.badge::before {
  content: ""; width: 7px; height: 7px; background: currentColor;
  clip-path: polygon(50% 0, 100% 100%, 0 100%);
}
.badge + .badge { margin-left: var(--spacing-12); }
.badge-on-time, .badge-arrived { color: var(--color-verdant-text); }
.badge-delayed { color: var(--color-saffron-spark); }
.badge-cancelled, .badge-diverted { color: var(--color-magenta); }
.badge-boarding, .badge-departed { color: var(--color-blue); }
.badge-link-aircraft { color: var(--color-iris-text); }
.badge-link-crew { color: var(--color-magenta); }
.badge-link-gate { color: var(--color-blue); }
.badge-link-slot { color: var(--color-verdant-text); }

/* ---------- detail lists ---------- */

.detail-grid { display: grid; grid-template-columns: minmax(170px, max-content) 1fr; gap: var(--spacing-12) var(--spacing-36); margin: 0 0 var(--spacing-24); }
.detail-grid dt {
  color: var(--color-ash-gray); font-size: var(--text-caption); line-height: var(--leading-caption);
  font-weight: var(--font-weight-semibold); letter-spacing: var(--tracking-nav-label);
  text-transform: uppercase; padding-top: 4px;
}
.detail-grid dd { margin: 0; font-size: var(--text-body); font-weight: var(--font-weight-extralight); }

/* ---------- Team Member Card (crew): violet role label above the name ---------- */

.person { margin: var(--spacing-24) 0 var(--spacing-60); }
.person .role {
  display: block; margin-bottom: var(--spacing-12);
  font-size: var(--text-caption); font-weight: var(--font-weight-regular);
  letter-spacing: var(--tracking-nav-label); text-transform: uppercase;
  color: var(--color-iris-text);
}
.person h1 { max-width: none; }
.person p { margin: var(--spacing-12) 0 0; }

/* ---------- forms: fields float on the void, underline only ---------- */

.form { display: flex; flex-direction: column; gap: var(--spacing-24); max-width: 520px; margin: 0; }
.form-wide { max-width: 980px; gap: var(--spacing-60); }
.form > .btn { align-self: flex-start; margin-top: var(--spacing-12); }
.field { display: flex; flex-direction: column; gap: var(--spacing-6); }
.field > span {
  color: var(--color-ash-gray); font-size: var(--text-caption);
  font-weight: var(--font-weight-semibold); letter-spacing: var(--tracking-nav-label); text-transform: uppercase;
}
input, select, textarea {
  width: 100%;
  padding: var(--spacing-12) 0;
  border: 0; border-bottom: 1px solid var(--line-field); border-radius: 0;
  background: transparent; color: var(--color-bone-white);
  font: var(--font-weight-extralight) var(--text-body)/1.4 var(--font-app);
  transition: border-color 0.15s ease;
}
input::placeholder, textarea::placeholder { color: #5f5f5f; }
input:hover, select:hover, textarea:hover { border-bottom-color: rgba(255, 255, 255, 0.45); }
input:focus, select:focus, textarea:focus { outline: none; border-bottom-color: var(--color-electric-iris); }
input:focus-visible, select:focus-visible, textarea:focus-visible { outline: none; box-shadow: 0 1px 0 0 var(--color-electric-iris); }
select {
  appearance: none; -webkit-appearance: none; padding-right: 28px;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='8'%3E%3Cpath d='M0 0h10L5 8z' fill='%239a9a9a'/%3E%3C/svg%3E");
  background-repeat: no-repeat; background-position: right 4px center;
}
select option, select optgroup { background: var(--surface-void-canvas); color: var(--color-bone-white); }
textarea { resize: vertical; line-height: var(--leading-body); }
input[type="checkbox"] { width: 18px; height: 18px; padding: 0; margin: 0; accent-color: var(--color-electric-iris); flex: none; }

fieldset { border: 0; padding: 0; margin: 0; min-width: 0; }
legend {
  padding: 0; margin-bottom: var(--spacing-24);
  font-size: var(--text-heading-2xs); line-height: var(--leading-heading-2xs);
  letter-spacing: var(--tracking-heading-2xs); font-weight: var(--font-weight-regular);
}
.grid-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: var(--spacing-24) var(--spacing-60); align-items: start; }
.grid-2 > div > h2:first-child { margin-top: var(--spacing-96); }
.checks { display: flex; flex-wrap: wrap; gap: var(--spacing-12) var(--spacing-30); margin-top: var(--spacing-24); }
.check { display: flex; align-items: center; gap: var(--spacing-12); font-size: var(--text-body); font-weight: var(--font-weight-extralight); cursor: pointer; }
fieldset .check { align-self: end; padding-bottom: var(--spacing-12); }

.filter-bar, .form-inline { display: flex; flex-wrap: wrap; align-items: flex-end; gap: var(--spacing-18) var(--spacing-30); margin: 0 0 var(--spacing-60); }
.filter-bar input, .filter-bar select, .form-inline input, .form-inline select { width: auto; min-width: 180px; }
.filter-bar input[type="search"] { min-width: 300px; }
.form-inline .btn { align-self: center; }

/* ---------- large-format link lists (reports, admin) ---------- */

.link-list { list-style: none; padding: 0; margin: 0; }
.link-list li { border-bottom: 1px solid var(--line-hairline); }
.link-list a {
  display: flex; align-items: baseline; justify-content: space-between; gap: var(--spacing-24);
  padding: var(--spacing-30) 0;
  font-size: clamp(26px, 3vw, var(--text-subheading)); line-height: var(--leading-subheading);
  letter-spacing: -0.03em; text-decoration: none;
}
.link-list a::after {
  content: ""; flex: none; width: 12px; height: 12px; background: var(--color-ash-gray);
  clip-path: polygon(0 0, 100% 50%, 0 100%);
  transition: background-color 0.15s ease, transform 0.15s ease;
}
.link-list a:hover::after { background: var(--color-saffron-spark); transform: translateX(4px); }
.link-list small {
  display: block; margin-top: var(--spacing-6);
  font-size: var(--text-body); font-weight: var(--font-weight-extralight);
  color: var(--color-ash-gray); letter-spacing: 0;
}

/* ---------- chips (airport shortcuts) ---------- */

.chip-row { display: flex; flex-wrap: wrap; gap: var(--spacing-12) var(--spacing-24); margin: 0 0 var(--spacing-24); }
.chip {
  font-size: 13px; font-weight: var(--font-weight-semibold); letter-spacing: var(--tracking-nav-em);
  text-decoration: none; color: var(--color-silver-mist); padding: var(--spacing-6) 0;
}
.chip:hover { color: var(--color-bone-white); }
.chip-late { color: var(--color-saffron-spark); }

/* ---------- Carousel Navigation Dot (airport board days) ---------- */

.dots { display: flex; flex-wrap: wrap; gap: var(--spacing-6) var(--spacing-24); margin: 0 0 var(--spacing-30); }
.dot-link {
  display: inline-flex; align-items: center; gap: var(--spacing-12);
  font-size: var(--text-nav-label); color: var(--color-ash-gray); text-decoration: none;
}
.dot-link::before {
  content: ""; width: 8px; height: 8px; border-radius: var(--radius-full);
  background: var(--color-ash-gray); opacity: 0.35;
}
.dot-link:hover { color: var(--color-bone-white); }
.dot-link[aria-current="date"] { color: var(--color-bone-white); }
.dot-link[aria-current="date"]::before { background: var(--color-electric-iris); opacity: 1; }

/* ---------- Hero: display headline left, constellation right ---------- */

.hero {
  display: grid; grid-template-columns: minmax(0, 5fr) minmax(0, 6fr);
  gap: var(--spacing-36); align-items: center;
  min-height: min(680px, 80vh);
  margin: calc(var(--spacing-12) * -1) 0 var(--spacing-96);
}
.hero h1 {
  font-size: clamp(56px, 8vw, var(--text-display));
  line-height: 0.95;
  letter-spacing: var(--tracking-display-em);
  max-width: 8ch;
}
.hero .label { margin: var(--spacing-36) 0 var(--spacing-12); }
.hero p { margin: 0 0 var(--spacing-36); color: var(--color-bone-white); max-width: 480px; }
.constellation { position: relative; aspect-ratio: 1 / 1.05; width: 100%; }
.constellation canvas { position: absolute; inset: 0; width: 100%; height: 100%; cursor: default; touch-action: pan-y; }
.constellation-tip {
  position: absolute; pointer-events: none; transform: translate(-50%, -100%);
  padding: var(--spacing-6) var(--spacing-12); background: rgba(0, 0, 0, 0.72);
  font-size: 13px; font-weight: var(--font-weight-semibold); letter-spacing: var(--tracking-nav-label); white-space: nowrap;
  color: var(--color-bone-white); opacity: 0;
  transition: opacity 0.12s ease, left 0.18s ease, top 0.18s ease;
}
.constellation-tip span { display: block; margin-top: 2px; font-weight: var(--font-weight-extralight); letter-spacing: 0; color: var(--color-silver-mist); }
.constellation-tip.is-late span { color: var(--color-saffron-spark); }
.constellation-legend { margin: var(--spacing-6) 0 0; max-width: none; text-align: right; }

/* ---------- airport board ---------- */

.board td { font-size: 16px; }
.board td:first-child { font-size: var(--text-body); white-space: nowrap; }
.board td:first-child, .board td:first-child * { font-variant-numeric: tabular-nums; }
.board s { color: #6b6b6b; text-decoration-thickness: 1px; }

/* ---------- responsive ---------- */

@media (max-width: 900px) {
  .topbar { flex-direction: column; align-items: flex-start; padding: var(--spacing-18) 16px; }
  .topbar nav { justify-content: flex-start; flex-wrap: nowrap; overflow-x: auto; max-width: 100%; padding-bottom: var(--spacing-6); }
  .topbar nav { flex: none; }
  .container { padding: var(--spacing-24) 16px var(--spacing-96); }
  .hero, .headline-block { grid-template-columns: 1fr; min-height: 0; }
  .hero-visual { order: -1; }
  .constellation { aspect-ratio: 1 / 0.9; }
  .constellation-legend { text-align: left; }
  .data-table { display: block; overflow-x: auto; }
  .data-table td { white-space: nowrap; }
  .filter-bar input, .filter-bar select, .filter-bar input[type="search"] { min-width: 0; width: 100%; }
  .detail-grid { grid-template-columns: 1fr; gap: 4px; }
  .detail-grid dd { margin-bottom: var(--spacing-12); }
  h2 { margin-top: var(--spacing-60); }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { transition: none !important; }
}

.table-scroll { overflow-x: auto; }
.table-scroll .data-table td { white-space: nowrap; }

/* ---------- live record (every column of the row, incl. ones added by ALTER TABLE) ---------- */

.record { margin-top: var(--spacing-96); border-top: 1px solid var(--line-hairline); padding-top: var(--spacing-24); }
.record summary {
  cursor: pointer; color: var(--color-ash-gray);
  font-size: var(--text-caption); font-weight: var(--font-weight-semibold);
  letter-spacing: var(--tracking-nav-label); text-transform: uppercase;
}
.record summary:hover { color: var(--color-bone-white); }
.record summary code { text-transform: none; }
.record[open] summary { margin-bottom: var(--spacing-24); }
.record dd { font-size: 15px; font-weight: var(--font-weight-regular); word-break: break-word; }
````

### A.96 `static/js/ambient.js`

````javascript
// Ambient Particle Field (DESIGN.md): sparse outlined triangles drifting at low
// opacity behind every page. Skipped on the dashboard, whose constellation
// already fills that role, and frozen when reduced motion is requested.
(() => {
  const canvas = document.getElementById("ambient-field");
  if (!canvas || document.getElementById("constellation")) return;
  const ctx = canvas.getContext("2d");
  const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const COLORS = ["#8052ff", "#ffb829", "#15846e", "#3ecfae", "#ff5fa2", "#5aa9ff"];
  let seed = 11;
  const rand = () => ((seed = (seed * 16807) % 2147483647) - 1) / 2147483646;
  const bits = Array.from({ length: 70 }, () => ({
    x: rand(), y: rand(), size: 1.5 + rand() * 3, rot: rand() * 6.28,
    vx: (rand() - 0.5) * 0.00006, vy: (rand() - 0.5) * 0.00006, spin: (rand() - 0.5) * 0.004,
    color: COLORS[Math.floor(rand() * COLORS.length)], alpha: 0.12 + rand() * 0.22,
  }));
  let W = 0, H = 0;
  function size() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = window.innerWidth; H = window.innerHeight;
    canvas.width = W * dpr; canvas.height = H * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  function draw() {
    ctx.clearRect(0, 0, W, H);
    ctx.lineWidth = 1;
    bits.forEach((b) => {
      if (!still) {
        b.x = (b.x + b.vx + 1) % 1; b.y = (b.y + b.vy + 1) % 1; b.rot += b.spin;
      }
      ctx.globalAlpha = b.alpha;
      ctx.strokeStyle = b.color;
      ctx.beginPath();
      for (let k = 0; k < 3; k++) {
        const a = b.rot + (k * 2 * Math.PI) / 3;
        const px = b.x * W + Math.cos(a) * b.size, py = b.y * H + Math.sin(a) * b.size;
        k ? ctx.lineTo(px, py) : ctx.moveTo(px, py);
      }
      ctx.closePath();
      ctx.stroke();
    });
    if (!still) requestAnimationFrame(draw);
  }
  window.addEventListener("resize", () => { size(); if (still) draw(); });
  size();
  draw();
})();
````

### A.97 `static/js/constellation.js`

````javascript
// The airline network drawn as a constellation of outlined triangles.
// Each airport is a cluster placed at its real position; particles drift along
// routes; airports with late departures burn amber. Hover shows the airport,
// click opens its board. Everything is also reachable via the chip links below.
(() => {
  const root = document.getElementById("constellation");
  if (!root) return;

  const airports = JSON.parse(root.dataset.airports);
  const routes = JSON.parse(root.dataset.routes);
  const canvas = root.querySelector("canvas");
  const tip = root.querySelector(".constellation-tip");
  const ctx = canvas.getContext("2d");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // [longitude, latitude]; airports added later without an entry sit on a ring.
  const COORDS = {
    DEL: [77.1, 28.56], BOM: [72.87, 19.09], BLR: [77.71, 13.2], MAA: [80.17, 12.99],
    CCU: [88.45, 22.65], HYD: [78.43, 17.24], PNQ: [73.92, 18.58], GOI: [73.83, 15.38],
    AMD: [72.63, 23.07], COK: [76.39, 10.15], LKO: [80.89, 26.76], JAI: [75.81, 26.82],
    TRV: [76.92, 8.48], IXC: [76.79, 30.67], PAT: [85.09, 25.59], BBI: [85.82, 20.25],
    GAU: [91.59, 26.11], NAG: [79.05, 21.09], IXB: [88.33, 26.68], VNS: [82.86, 25.45],
  };
  const SPECTRUM = ["#8052ff", "#a386ff", "#3ecfae", "#15846e", "#ff5fa2", "#5aa9ff"];
  const AMBER = "#ffb829";

  // Deterministic pseudo-random so the constellation keeps its shape between reloads.
  let seed = 7;
  const rand = () => ((seed = (seed * 16807) % 2147483647) - 1) / 2147483646;
  const gauss = () => {
    let u = 0, v = 0;
    while (!u) u = rand();
    while (!v) v = rand();
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
  };

  const degree = {};
  routes.forEach(([a, b]) => { degree[a] = (degree[a] || 0) + 1; degree[b] = (degree[b] || 0) + 1; });
  const byId = Object.fromEntries(airports.map((a) => [a.id, a]));
  const neighbours = {};
  routes.forEach(([a, b]) => {
    (neighbours[a] = neighbours[a] || new Set()).add(b);
    (neighbours[b] = neighbours[b] || new Set()).add(a);
  });

  airports.forEach((a, i) => {
    const c = COORDS[a.iata];
    a.lon = c ? c[0] : 80 + 9 * Math.cos((i / airports.length) * 2 * Math.PI);
    a.lat = c ? c[1] : 20 + 9 * Math.sin((i / airports.length) * 2 * Math.PI);
    // Busier airports (more routes, more departures) get bigger, denser clusters.
    a.count = Math.min(170, Math.round(22 + (degree[a.id] || 1) * 4 + a.deps * 1.5));
    a.spread = 3 + Math.sqrt(a.count) * 0.95;
    // Amber share grows with the airport's late departures.
    const lateShare = a.late ? Math.min(0.65, 0.15 + a.late * 0.05) : 0;
    a.particles = Array.from({ length: a.count }, () => ({
      dx: gauss() * a.spread,
      dy: gauss() * a.spread,
      size: 1.6 + rand() * 3.4,
      rot: rand() * Math.PI * 2,
      phase: rand() * Math.PI * 2,
      speed: 0.3 + rand() * 0.7,
      color: rand() < lateShare ? AMBER : SPECTRUM[Math.floor(rand() * SPECTRUM.length)],
      sx: rand(), sy: rand(), // scattered start, for the entrance
      ox: 0, oy: 0, // eased push-away from the cursor
    }));
    a.vis = 1;   // eased visibility: fades when another airport is hovered
    a.glow = 0;  // eased hover emphasis
    a.burst = 0; // click burst, 0..1
  });

  const streams = [];
  routes.forEach(([a, b]) => {
    if (!byId[a] || !byId[b]) return;
    const n = 2 + Math.floor(rand() * 3);
    for (let i = 0; i < n; i++) {
      streams.push({
        a: byId[a], b: byId[b], t: rand(), speed: 0.0006 + rand() * 0.0012,
        bend: (rand() - 0.5) * 0.35, size: 1.4 + rand() * 1.8,
        color: SPECTRUM[Math.floor(rand() * SPECTRUM.length)], reverse: rand() < 0.5,
      });
    }
  });

  const ambient = Array.from({ length: 110 }, () => ({
    x: rand(), y: rand(), size: 1.2 + rand() * 2.4, rot: rand() * 6.28,
    phase: rand() * 6.28, color: SPECTRUM[Math.floor(rand() * SPECTRUM.length)],
    ox: 0, oy: 0,
  }));

  let W = 0, H = 0, hovered = null;
  const lons = airports.map((a) => a.lon), lats = airports.map((a) => a.lat);
  const bounds = {
    minLon: Math.min(...lons) - 1.5, maxLon: Math.max(...lons) + 1.5,
    minLat: Math.min(...lats) - 1.5, maxLat: Math.max(...lats) + 1.5,
  };

  function layout() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = root.clientWidth; H = root.clientHeight;
    canvas.width = W * dpr; canvas.height = H * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const pad = 36;
    const sx = (W - pad * 2) / (bounds.maxLon - bounds.minLon);
    const sy = (H - pad * 2) / (bounds.maxLat - bounds.minLat);
    const s = Math.min(sx, sy);
    const ox = (W - s * (bounds.maxLon - bounds.minLon)) / 2;
    const oy = (H - s * (bounds.maxLat - bounds.minLat)) / 2;
    const scale = Math.max(0.55, Math.min(1.1, W / 640));
    airports.forEach((a) => {
      a.x = ox + (a.lon - bounds.minLon) * s;
      a.y = oy + (bounds.maxLat - a.lat) * s;
      a.scale = scale;
    });
  }

  function tri(path, x, y, size, rot) {
    for (let k = 0; k < 3; k++) {
      const ang = rot + (k * 2 * Math.PI) / 3;
      const px = x + Math.cos(ang) * size, py = y + Math.sin(ang) * size;
      k ? path.lineTo(px, py) : path.moveTo(px, py);
    }
    path.closePath();
  }

  const ease = (t) => 1 - Math.pow(1 - Math.min(1, t), 3);
  const start = performance.now();
  const pointer = { x: 0, y: 0, active: false };
  let focus = null;    // airport whose network is highlighted (kept while fading out)
  let hoverMix = 0;    // eased 0..1: how strongly the highlight is showing
  let leaving = false; // a click is navigating away

  const approach = (from, to, k) => from + (to - from) * k;
  const isLinked = (a) => focus && (a === focus || neighbours[focus.id]?.has(a.id));

  // Push a point away from the cursor; returns the eased offset stored on p.
  function repel(p, x, y, radius, strength) {
    let tx = 0, ty = 0;
    if (pointer.active && !reduceMotion) {
      const dx = x - pointer.x, dy = y - pointer.y;
      const d = Math.hypot(dx, dy);
      if (d < radius && d > 0.01) {
        const f = Math.pow(1 - d / radius, 2) * strength;
        tx = (dx / d) * f; ty = (dy / d) * f;
      }
    }
    p.ox = approach(p.ox, tx, 0.16);
    p.oy = approach(p.oy, ty, 0.16);
  }

  function frame() {
    // performance.now() rather than the rAF timestamp: some browsers hand rAF a
    // timestamp from an earlier origin, which stalls the entrance.
    const time = (performance.now() - start) / 1000;
    const enter = reduceMotion ? 1 : ease(time / 1.8);
    const k = reduceMotion ? 1 : 0.12;

    hoverMix = approach(hoverMix, hovered ? 1 : 0, k);
    if (hovered) focus = hovered;
    else if (hoverMix < 0.02) focus = null;
    airports.forEach((a) => {
      a.vis = approach(a.vis, !focus || isLinked(a) ? 1 : 0.22, k);
      a.glow = approach(a.glow, a === hovered ? 1 : 0, k);
      if (a.burst) a.burst = Math.min(1, a.burst + 0.07);
    });

    ctx.clearRect(0, 0, W, H);
    const paths = new Map(); // "color|alpha" -> Path2D, so each colour is stroked once
    const pathFor = (color, alpha) => {
      const key = color + "|" + Math.round(Math.max(0, Math.min(1, alpha)) * 20) / 20;
      if (!paths.has(key)) paths.set(key, new Path2D());
      return paths.get(key);
    };

    ambient.forEach((p) => {
      const drift = reduceMotion ? 0 : Math.sin(time * 0.2 + p.phase) * 6;
      const x = p.x * W + drift, y = p.y * H + drift * 0.6;
      repel(p, x, y, 110, 34);
      tri(pathFor(p.color, 0.22), x + p.ox, y + p.oy, p.size, p.rot + time * 0.05);
    });

    // Faint arcs from the focused airport to every airport it serves.
    if (focus && hoverMix > 0.01) {
      ctx.lineWidth = 1;
      neighbours[focus.id]?.forEach((id) => {
        const b = byId[id];
        if (!b) return;
        const mx = (focus.x + b.x) / 2 - (b.y - focus.y) * 0.12;
        const my = (focus.y + b.y) / 2 + (b.x - focus.x) * 0.12;
        ctx.globalAlpha = 0.28 * hoverMix * enter;
        ctx.strokeStyle = b.late ? AMBER : "#a386ff";
        ctx.beginPath();
        ctx.moveTo(focus.x, focus.y);
        ctx.quadraticCurveTo(mx, my, b.x, b.y);
        ctx.stroke();
      });
      ctx.globalAlpha = 1;
    }

    streams.forEach((s) => {
      const onFocus = focus && (s.a === focus || s.b === focus);
      if (!reduceMotion) s.t = (s.t + s.speed * (onFocus ? 1 + 2 * hoverMix : 1)) % 1;
      const t = s.reverse ? 1 - s.t : s.t;
      const mx = (s.a.x + s.b.x) / 2 - (s.b.y - s.a.y) * s.bend;
      const my = (s.a.y + s.b.y) / 2 + (s.b.x - s.a.x) * s.bend;
      const x = (1 - t) * (1 - t) * s.a.x + 2 * (1 - t) * t * mx + t * t * s.b.x;
      const y = (1 - t) * (1 - t) * s.a.y + 2 * (1 - t) * t * my + t * t * s.b.y;
      const base = Math.sin(Math.PI * t) > 0.5 ? 0.55 : 0.25;
      const alpha = onFocus ? approach(base, 1, hoverMix) : base * (1 - 0.8 * hoverMix);
      tri(pathFor(s.color, alpha), x, y, s.size * (onFocus ? 1 + 0.4 * hoverMix : 1), t * 6);
    });

    airports.forEach((a) => {
      const swell = 1 + 0.22 * a.glow + 2.2 * ease(a.burst);
      const spin = reduceMotion ? 0 : time * (0.15 + 0.9 * a.glow);
      const alpha = (0.3 + 0.6 * a.vis) * (1 - a.burst);
      a.particles.forEach((p) => {
        const wob = reduceMotion ? 0 : Math.sin(time * p.speed + p.phase) * 1.6;
        const tx = a.x + p.dx * a.scale * swell + wob, ty = a.y + p.dy * a.scale * swell - wob;
        const bx = p.sx * W + (tx - p.sx * W) * enter;
        const by = p.sy * H + (ty - p.sy * H) * enter;
        repel(p, bx, by, a === hovered ? 40 : 80, a === hovered ? 10 : 26);
        tri(pathFor(p.color, alpha), bx + p.ox, by + p.oy, p.size * (1 + 0.25 * a.glow), p.rot + spin * p.speed);
      });
    });

    ctx.lineWidth = 1;
    ctx.lineJoin = "miter";
    for (const [key, path] of paths) {
      const [color, alpha] = key.split("|");
      if (Number(alpha) === 0) continue;
      ctx.globalAlpha = Number(alpha);
      ctx.strokeStyle = color;
      ctx.stroke(path);
    }
    ctx.globalAlpha = 1;

    // Airport codes, fading in once the clusters have formed.
    ctx.textBaseline = "middle";
    ctx.lineJoin = "round";
    ctx.lineWidth = 4;
    ctx.strokeStyle = "#000";
    airports.forEach((a) => {
      const lx = a.x + a.spread * a.scale * (1.6 + 0.35 * a.glow) + 4;
      ctx.font = `600 ${11 + 3 * a.glow}px Inter, system-ui, sans-serif`;
      ctx.globalAlpha = enter * (0.35 + 0.65 * a.vis);
      ctx.strokeText(a.iata, lx, a.y);
      ctx.fillStyle = a.glow > 0.5 ? "#ffffff" : a.late ? AMBER : "#bdbdbd";
      ctx.fillText(a.iata, lx, a.y);
    });
    ctx.globalAlpha = 1;

    if (!reduceMotion) requestAnimationFrame(frame);
  }

  function airportAt(x, y) {
    let best = null, bestD = Infinity;
    airports.forEach((a) => {
      const d = Math.hypot(a.x - x, a.y - y);
      if (d < Math.max(40, a.spread * a.scale * 2.4) && d < bestD) { best = a; bestD = d; }
    });
    return best;
  }

  function showTip(a) {
    const routesCount = neighbours[a.id]?.size || 0;
    tip.replaceChildren(`${a.iata}  ${a.city}`);
    const sub = document.createElement("span");
    const parts = [`${a.deps} departures today`];
    if (a.late) parts.push(`${a.late} running late`);
    parts.push(`${routesCount} ${routesCount === 1 ? "route" : "routes"}`);
    sub.textContent = parts.join(", ");
    tip.append(sub);
    tip.classList.toggle("is-late", a.late > 0);
    tip.style.left = a.x + "px";
    tip.style.top = a.y - a.spread * a.scale * 1.3 + "px";
    tip.style.opacity = 1;
  }

  function onMove(evt) {
    const r = canvas.getBoundingClientRect();
    pointer.x = evt.clientX - r.left;
    pointer.y = evt.clientY - r.top;
    pointer.active = true;
    const a = airportAt(pointer.x, pointer.y);
    if (a !== hovered && !leaving) {
      hovered = a;
      canvas.style.cursor = a ? "pointer" : "default";
      a ? showTip(a) : (tip.style.opacity = 0);
    }
    if (reduceMotion) requestAnimationFrame(frame);
  }

  canvas.addEventListener("pointermove", onMove);
  canvas.addEventListener("pointerdown", onMove);
  canvas.addEventListener("pointerleave", () => {
    pointer.active = false;
    if (leaving) return;
    hovered = null; tip.style.opacity = 0; canvas.style.cursor = "default";
    if (reduceMotion) requestAnimationFrame(frame);
  });
  canvas.addEventListener("click", (evt) => {
    const r = canvas.getBoundingClientRect();
    const a = airportAt(evt.clientX - r.left, evt.clientY - r.top);
    if (!a || leaving) return;
    if (reduceMotion) { window.location.href = a.url; return; }
    leaving = true;
    a.burst = 0.01;
    setTimeout(() => { window.location.href = a.url; }, 320);
  });
  // Coming back via the browser's back button restores the page from cache mid-burst.
  window.addEventListener("pageshow", (evt) => {
    if (!evt.persisted) return;
    leaving = false;
    airports.forEach((a) => { a.burst = 0; });
  });

  new ResizeObserver(() => { layout(); if (reduceMotion) requestAnimationFrame(frame); }).observe(root);
  layout();
  requestAnimationFrame(frame);
})();
````

### A.98 `requirements.txt`

````text
flask==3.0.0
mysql-connector-python==8.2.0
python-dotenv==1.0.0
````

### A.99 `.env.example`

````bash
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=airline_cascades
````

### A.100 `.gitignore`

````text
.env
__pycache__/
*.pyc
.venv/
venv/
.DS_Store
*.log
````

### A.101 `README.md`

````markdown
# Airline Cascades — DBMS CIA 3 Project

Airline operations and delay-cascade simulator. File a delay on any flight
(IATA delay code, minutes or new ETD, gate change, aircraft swap, passenger
announcement, meal voucher/compensation, who reported it) and the database
cascades it across the whole airline:

- **Aircraft** — the same plane's later legs slip (minimum turnaround per airport)
- **Crew** — flights waiting for crew who are arriving on a late flight
- **Gates** — the next flight at a gate can't board until it's free
- **Runway slots** — each airport's departures-per-hour limit
- **Passengers** — missed connections, crew duty-limit breaches and curfew
  risks are flagged (from views, never stored)

Every knock-on change is logged, so each delay has an impact page listing
every flight that moved, why, and its old → new times. Airport boards show
scheduled vs estimated times for every airport.

Demo data: 20 airports with gates and operating rules, 40 aircraft on
realistic hub-and-spoke rotations, 1,400 flights over 7 days, 400 crew,
2,000 passengers, 15,000 tickets (incl. connecting journeys).

19-table schema (3NF, two documented denormalizations), 4 views, 3 triggers,
6 stored procedures, full CRUD across every entity.

## Prerequisites

- Python 3.9+
- MySQL 8.0+ running locally (needed for `WITH RECURSIVE` and `CHECK` constraint enforcement)
- pip

## Setup (three commands)

```
cp .env.example .env      # then edit .env with your MySQL password
pip install -r requirements.txt
bash scripts/setup_db.sh
```

## Run

```
python app.py
```

Open http://localhost:5000

## Demo walkthrough

1. **Flights** → press **Delay** on any upcoming flight (or on an airport board).
2. Pick an IATA code and type the minutes (or a new ETD); the form fills in
   the new ETA, boarding time, vouchers and a draft announcement.
3. **File delay & cascade** → the impact page shows every flight it moved.
4. **Airports** → **Board** to see scheduled vs estimated times.
5. **Delays** → **Reset all delays** to put everything back on schedule.

All reference data (airports and their timings, gates, delay codes, routes,
aircraft) is editable under **Admin** / **Airports**.

## Check

Each check changes data, so run it on a freshly seeded database:

```
bash scripts/setup_db.sh && python tests/test_cascade.py
bash scripts/setup_db.sh && python tests/test_crew_assignment.py
python tests/test_live_changes.py   # manual MySQL edits show on the site (rebuilds the DB itself)
```

## Changing tables by hand (viva)

Edits made directly in MySQL show on the next page load: rows (INSERT/UPDATE/DELETE),
new columns (every detail page has an "All columns" section; admin forms pick them up),
new ENUM values (every dropdown reads them live), new tables and views (Schema page,
with a row browser). A change that breaks a page's query shows MySQL's exact error.
If your MySQL client has autocommit off, `COMMIT` first.

## Report

`python scripts/build_report_context.py` regenerates `docs/REPORT_CONTEXT.md`: the
whole project (design, SQL, data, live test results, a measured cascade, screenshots
list and full source) in one file to hand to Claude for writing the report.

## Docs

- `docs/CRUD_MATRIX.md` — which UI page implements each CRUD cell
- `docs/NORMALIZATION.md` — per-table 3NF justification
- `docs/VIVA_PREP.md` — Q&A for oral defence
- `docs/SCHEMA_DIAGRAM.md` — relationship description
- `docs/DEVIATIONS.md` — spec deviations
- `docs/superpowers/specs/2026-09-23-org-wide-delay-cascade-design.md` — cascade design
- `docs/REPORT_CONTEXT.md` — everything needed to write the project report (design, SQL, data, measured results)
````

### A.102 `docs/CRUD_MATRIX.md`

````markdown
# CRUD matrix

Which UI page/route implements each CRUD operation, per entity.

| Entity | Create | Read | Update | Delete |
|---|---|---|---|---|
| **Flight** | `GET/POST /flights/new` | `GET /flights/`, `GET /flights/<id>` | `GET/POST /flights/<id>/edit` | `POST /flights/<id>/delete` |
| **Crew** | `GET/POST /crew/new` | `GET /crew/`, `GET /crew/<id>` | `GET/POST /crew/<id>/edit` | `POST /crew/<id>/delete` |
| **Crew certification** | `POST /crew/<id>/certify` | `GET /crew/<id>` (embedded) | — (remove + re-add) | `POST /crew/<id>/certify/<type_id>/delete` |
| **Crew assignment** | `POST /flights/<id>/assign-crew` | `GET /flights/<id>` (embedded) | — | `POST /flights/<id>/unassign-crew/<crew_id>` |
| **Passenger** | `GET/POST /passengers/new` | `GET /passengers/`, `GET /passengers/<id>` | `GET/POST /passengers/<id>/edit` | `POST /passengers/<id>/delete` |
| **Booking** | `GET/POST /bookings/new` (via `book_ticket()`) | `GET /bookings/`, `GET /bookings/<id>` | — (cancel is the only status transition) | `POST /bookings/<id>/cancel` (soft delete) |
| **Ticket** | `POST /bookings/<id>/ticket` | `GET /bookings/<id>` (embedded) | `POST /bookings/ticket/<id>/checkin` (check-in only) | — (cascades with its booking) |
| **Delay notice** | `GET/POST /flights/<id>/delay` (via `simulate_delay()`) | `GET /delays/`, `GET /delays/<id>` (impact page), `GET /flights/<id>` | `GET/POST /delays/<id>/edit` (non-timing fields), `POST /delays/<id>/resolve` | `GET/POST /delays/reset` (all, via `reset_all_delays()`) |
| **Airport** (incl. hours, slots, MCT, turnaround) | `GET/POST /admin/airport/new` | `GET /airports/`, `GET /airports/<id>/board`, `GET /admin/airport/` | `GET/POST /admin/airport/<id>/edit` | `POST /admin/airport/<id>/delete` |
| **Gate** | `GET/POST /admin/gate/new` | `GET /admin/gate/` | `GET/POST /admin/gate/<id>/edit` | `POST /admin/gate/<id>/delete` |
| **IATA delay code** | `GET/POST /admin/delay_code/new` | `GET /admin/delay_code/` | `GET/POST /admin/delay_code/<id>/edit` | `POST /admin/delay_code/<id>/delete` |
| **Aircraft type** | `GET/POST /admin/aircraft_type/new` | `GET /admin/aircraft_type/` | `GET/POST /admin/aircraft_type/<id>/edit` | `POST /admin/aircraft_type/<id>/delete` |
| **Delay reason** | `GET/POST /admin/delay_reason/new` | `GET /admin/delay_reason/` | `GET/POST /admin/delay_reason/<id>/edit` | `POST /admin/delay_reason/<id>/delete` |
| **Route** | `GET/POST /admin/route/new` | `GET /admin/route/` | `GET/POST /admin/route/<id>/edit` | `POST /admin/route/<id>/delete` |
| **Aircraft** | `GET/POST /admin/aircraft/new` | `GET /admin/aircraft/` | `GET/POST /admin/aircraft/<id>/edit` | `POST /admin/aircraft/<id>/delete` |
| **Maintenance log** | `GET/POST /admin/maintenance_log/new` | `GET /admin/maintenance_log/` | `GET/POST /admin/maintenance_log/<id>/edit` | `POST /admin/maintenance_log/<id>/delete` |

## Read-only / system-maintained (no direct CRUD, by design)

- **`delay_impact`** — written only by `simulate_delay()`, one row per
  knock-on change; shown on each delay's impact page and on the affected
  flight's page. Editing one by hand would leave `flight.delay_minutes` out
  of sync with it.
- **`duty_log`** — maintained entirely by `trg_update_duty` and read on the
  crew duty-status report. It has no independent existence outside what
  flights a crew member actually flew.

## Non-CRUD actions (the project's centerpiece)

- **File a delay** — `POST /flights/<id>/delay`, calls `simulate_delay()`,
  which records the notice and cascades it across aircraft, crew, gates and
  runway slots until nothing else moves.
- **Trace a cascade** — `GET /cascade/<flight_id>`, calls
  `analyse_cascade()` (recursive CTE over `parent_flight_id`) and lists
  affected passengers.
- **Find replacement crew** — `GET /crew/replacement/<flight_id>`, calls
  `find_replacement_crew()`.
````

### A.103 `docs/DEVIATIONS.md`

````markdown
# Deviations from the original spec

Every deviation below was forced by a real MySQL 8 restriction (or, in one
case, a local build quirk), not a design preference. Each is also noted as an
inline comment at the point in the SQL where it applies.

## 1. `passenger.age` is not a generated column

MySQL 8 disallows non-deterministic functions (`CURDATE()`, `NOW()`) in
generated column expressions (error 3763). Age is instead computed at query
time with `TIMESTAMPDIFF(YEAR, date_of_birth, CURDATE())` wherever it's
needed, rather than stored.

## 2. `date_of_birth must be in the past` is not a CHECK constraint

Same root cause: MySQL 8 disallows non-deterministic functions in `CHECK`
expressions (error 3814). Enforced instead in the Flask form
(`src/routes/passengers.py::_validate_dob`) before the INSERT/UPDATE reaches
the database.

## 3. `chk_no_self_parent` was dropped from `flight`

MySQL 8 disallows a column from being used in a `CHECK` constraint when that
same column also has a foreign-key referential action attached
(`parent_flight_id` has `ON DELETE SET NULL` — error 3823). The invariant
("a flight can't be its own cascade parent") still holds in practice: the
only writer of `parent_flight_id` is `simulate_delay()`, and its `JOIN`
condition (`downstream.flight_id <> origin.flight_id`) guarantees a flight
never becomes its own parent.

## 4. The cascade is a stored procedure, not a self-updating trigger

The original design called for an `AFTER UPDATE ON flight` trigger that
itself updates `flight` to propagate delays. MySQL rejects this at runtime
with error 1442 ("Can't update table 'flight' in stored function/trigger
because it is already used by statement which invoked this stored
function/trigger") — a real MySQL restriction on mutating a table from its
own trigger. The design also assumed the trigger would recursively re-fire
itself to walk multi-hop chains; MySQL does not support trigger
self-recursion either.

The cascade is implemented instead as an iterative stored procedure,
`simulate_delay()` (`05_procedures.sql`), invoked explicitly by the
"Delay" button on each flight. Each pass of its `WHILE` loop asks four
rules (aircraft turnaround, crew connection, gate occupancy, runway slots —
`compute_cascade_candidates()`) what delay every not-yet-departed flight now
requires, and raises `delay_minutes` wherever the requirement exceeds it; the
loop stops once a pass changes no rows (`ROW_COUNT() = 0`). `delay_minutes` only ever
increases, so the loop always terminates on its own; the 50-iteration cap
is a defensive backstop.

## 5. `book_ticket()` generates the PNR with `UUID()`, not `MD5(RAND())`

On MySQL builds linked against an OpenSSL 3.x "default" provider with the
legacy provider disabled (this is the case for the Homebrew `mysql` formula
used in local development), `MD5()` and `SHA1()` are unavailable — calling
either raises `FUNCTION db.MD5 does not exist`, even though the function
exists on a standard MySQL build. `UUID()` has no such dependency and is
equally suitable for generating a random 6-character PNR
(`UPPER(SUBSTRING(REPLACE(UUID(), '-', ''), 1, 6))`).

## 6. The cascade engine's scratch table is a regular table, not `TEMPORARY`

Each pass of `simulate_delay()` collects every rule's requirement into
`cascade_candidate`, then picks the largest per flight with a window
function over that same table. MySQL can't open a `TEMPORARY` table more than
once in one statement (error 1137, "Can't reopen table"), so it's a regular
table that the procedure empties at the start of each pass and again before
committing. The seed script's staging tables (`seed_leg`, `seed_team`, ...)
are regular tables for the same reason, and are dropped at the end of the
seed.

## 7. Crew connection time and duty limit are fixed in SQL

The crew rule uses a fixed 45-minute crew connection time, and
`v_duty_breaches` a fixed 13-hour flight-duty limit (first departure to last
arrival). Airports carry their own turnaround and passenger connection times
because those genuinely differ by airport; crew rules are airline-wide, so a
per-airport column would add configuration nobody changes.
````

### A.104 `docs/NORMALIZATION.md`

````markdown
# Normalization

All 19 tables are in 3NF: every non-key attribute depends on the whole
primary key and nothing but the key. Two attributes are deliberately
denormalized, both for performance, and both are maintained exclusively by
triggers/procedures rather than by application code, so they never drift out
of sync with the data they're derived from.

## Per-table 3NF justification

| Table | Key | Notes |
|---|---|---|
| `airport` | `airport_id` | All attributes (IATA/ICAO code, city, country, timezone, opening hours, runway slots per hour, minimum connection and turnaround times) describe the airport itself. |
| `gate` | `gate_id`, unique on (`airport_id`, `gate_code`) | Terminal depends on the gate. |
| `delay_code` | `code_id`, unique on `iata_code` | Description and category depend on the code. |
| `aircraft_type` | `type_id` | Seat capacity, range, cruise speed are all properties of the type, not of any individual aircraft. |
| `delay_reason` | `reason_id` | `category` + `description` describe the reason only. |
| `route` | `route_id` | Distance and standard duration depend on the origin/destination pair, not on any one flight. |
| `aircraft` | `aircraft_id` | Registration, type, base airport, status all describe one physical aircraft. |
| `crew` | `crew_id` | Name, role, base, hire date describe the crew member only. |
| `passenger` | `passenger_id` | No transitive dependency on booking or ticket data. |
| `flight` | `flight_id` | Schedule/actual times, status, and delay describe one flight instance — not the route (routes repeat across many flights) or the aircraft. |
| `crew_certification` | (`crew_id`, `type_id`) | Certification dates depend on the crew+type pair, not on either alone. |
| `duty_log` | `log_id`, unique on (`crew_id`, `duty_date`) | Hours depend on the crew member and the specific day. |
| `maintenance_log` | `maint_id` | Start/end/type describe one maintenance event on one aircraft. |
| `booking` | `booking_id` | PNR and status describe the booking as a passenger-facing unit, independent of which flights it covers. |
| `crew_assignment` | (`flight_id`, `crew_id`) | Role-on-this-flight depends on the pair. |
| `flight_delay` | `delay_id` | One delay notice: its code, minutes, phase, gate change, swap, passenger care flags and audit fields all describe that notice. The category is **not** stored here — it's reached through `delay_code` (code → category is a fact about the code, so a copy here would be a transitive dependency). |
| `delay_impact` | `impact_id` | One knock-on change: which notice, which flight, which link, and the before/after ETD at that moment. `old_etd`/`new_etd` are a historical record of that moment, not derivable later once other delays move the flight again. |
| `cascade_candidate` | — | Scratch table, emptied at the end of every `simulate_delay()` call; holds no persistent facts. |
| `ticket` | `ticket_id` | Seat, fare, class describe one seat on one flight within one booking — a booking can cover several flights (e.g. a connection), so this can't be folded into `booking`. |

## The two documented denormalizations

1. **`flight.delay_minutes`** — the running total delay for a flight. In
   3NF it's derivable as the flight's own `flight_delay.minutes` plus the
   `delay_impact.minutes_added` it received from other flights, but it's
   read by every rule in every pass of the cascade engine, every flight list
   and every report, so it's kept as a maintained column instead. It is
   written only by `simulate_delay()` and `reset_all_delays()`
   (`05_procedures.sql`), each in one transaction together with the
   notice/impact rows it summarizes; `tests/test_cascade.py` checks the
   equality holds.

   Estimated times are *not* stored: ETD/ETA are always computed as scheduled
   time + `delay_minutes` in `v_flight_times`, and missed connections, duty
   breaches and curfew risks are views too, so none of them can go stale.

2. **`duty_log.hours_flown` / `duty_log.hours_on_duty`** — running totals of
   a crew member's flown/on-duty hours for a given day. These are derivable
   from `crew_assignment` joined to `flight.actual_departure`/
   `actual_arrival`, but they're checked on every crew assignment
   (`trg_check_duty_limit`, before insert) and read on the duty-status
   report, so recomputing the join each time would be wasteful. They're
   maintained by `trg_update_duty` (`04_triggers.sql`), which fires
   `AFTER UPDATE ON flight` whenever `actual_arrival` is newly set, and
   upserts the day's totals for every crew member assigned to that flight.
````

### A.105 `docs/SCHEMA_DIAGRAM.md`

````markdown
# Schema diagram (relationship description)

19 tables and 4 views, organized into 4 dependency layers (as laid out in
`database/01_schema.sql`) — each layer only references tables in layers
above it. The live schema, with column types and keys, is also browsable at
runtime under **Schema** in the app (backed by `information_schema`).

## Layer 1 — no foreign keys

- **`airport`** — `airport_id` PK
- **`aircraft_type`** — `type_id` PK
- **`delay_reason`** — `reason_id` PK

## Layer 2 — reference Layer 1

- **`gate`** → `airport` (gates and terminals at each airport)
- **`delay_code`** → `delay_reason` (IATA AHM 730 codes, each in one category)
- **`route`** → `airport` (origin), `airport` (destination)
- **`aircraft`** → `aircraft_type`, `airport` (base)
- **`crew`** → `airport` (base)
- **`passenger`** — no FKs (referenced by `booking`)

## Layer 3 — reference Layer 2

- **`flight`** → `route`, `aircraft`, `gate` (departure gate), and **`flight`** itself
  (`parent_flight_id`, self-referencing — this is what makes the cascade a
  recursive structure: a flight's `parent_flight_id` points at the upstream
  flight that caused its delay)
- **`crew_certification`** → `crew`, `aircraft_type`
- **`duty_log`** → `crew`
- **`maintenance_log`** → `aircraft`
- **`booking`** → `passenger`

## Layer 4 — reference Layer 3

- **`crew_assignment`** → `flight`, `crew` (composite PK on the pair —
  models the many-to-many between flights and crew)
- **`flight_delay`** (a delay notice) → `flight`, `delay_code`, `gate` (gate
  change), `aircraft` (swap)
- **`delay_impact`** → `flight_delay`, `flight` (affected), `flight` (cause) —
  one row per knock-on change the cascade engine made
- **`cascade_candidate`** — no FKs; the engine's per-pass scratch table
- **`ticket`** → `booking`, `flight`

## Views

- **`v_flight_times`** — every flight with ETD/ETA (scheduled + `delay_minutes`),
  gate and display status (ON TIME / DELAYED / ...)
- **`v_missed_connections`** — bookings whose onward flight now leaves sooner
  than the connecting airport's minimum connection time
- **`v_duty_breaches`** — crew whose first-departure-to-last-arrival exceeds 13 h
- **`v_curfew_risk`** — flights now departing/arriving outside airport opening hours

## The cascade relationship

`flight.parent_flight_id → flight.flight_id` is the one self-referencing
edge in the schema. It's what `analyse_cascade()`'s recursive CTE walks:
starting from a root flight, it follows every flight whose
`parent_flight_id` points back into the set already visited, one level per
`UNION ALL` iteration, producing the full downstream delay tree.

The full organisation-wide cascade doesn't need an FK per link: aircraft,
crew and gate links are found by `LAG()` over flights partitioned by
aircraft, crew member and gate, and slot limits by `ROW_NUMBER()` over
departures per airport-hour (`compute_cascade_candidates()`).
`parent_flight_id` records the flight that caused each knock-on delay, and
`delay_impact` records every change with its link type.

## Delete behavior at a glance

Most FKs are `ON DELETE RESTRICT` (you can't delete an airport, route,
aircraft, or aircraft type that's still referenced) — appropriate for
reference data. The exceptions:

- `crew_certification`, `duty_log`, `crew_assignment`, `flight_delay`,
  `delay_impact`, `gate` are `ON DELETE CASCADE` from their parent (deleting a crew member or flight
  cleans up its dependent rows).
- `maintenance_log` is `ON DELETE CASCADE` from `aircraft`.
- `ticket` is `ON DELETE RESTRICT` from `flight` (a flight with sold tickets
  can't be deleted outright — cancel it instead) but `ON DELETE CASCADE`
  from `booking` (cancelling/deleting a booking removes its tickets).
- `flight.parent_flight_id` is `ON DELETE SET NULL` (deleting an upstream
  flight doesn't delete the downstream ones — it just detaches them from
  the cascade tree).
````

### A.106 `docs/VIVA_PREP.md`

````markdown
# Viva prep — Q&A

## Design

**Q: Why is the cascade a stored procedure instead of a trigger, if the
whole point is that a delay automatically propagates?**
A trigger that fires `AFTER UPDATE ON flight` and itself updates `flight`
hits MySQL error 1442 (a table can't be updated by a trigger while it's
already being used by the statement that invoked that trigger) — and the
design also needed the propagation to walk multiple hops, which would
require the trigger to re-fire itself, which MySQL also doesn't support.
`simulate_delay()` gets the same "one action delays everything downstream"
behavior by looping until a pass changes zero rows, driven explicitly by the
user filing a delay (the **Delay** button) rather than an UPDATE statement. See
`docs/DEVIATIONS.md` §4.

**Q: How do you know `simulate_delay()`'s loop terminates?**
Each pass only ever *increases* `delay_minutes` on rows it touches (a flight
is only updated when a rule requires more delay than it already has), and
the slot rule only ever moves flights later. Once a pass
makes no changes (`ROW_COUNT() = 0`), the loop exits. Delay is a
monotonically non-decreasing quantity being pushed through a finite set of
flights, so the loop can't cycle forever — the 50-iteration cap is a
backstop, not something the logic actually relies on.

**Q: Why is `flight.delay_minutes` a stored column instead of computed from
`flight_delay`?**
It's read on every flight list, the dashboard, and several reports; summing
`flight_delay` on every read would be wasteful for a value that changes
rarely. It's a documented denormalization, and it's written in exactly one
place (`simulate_delay()`), so it can't drift out of sync with the
`flight_delay` rows it summarizes.

**Q: What stops a flight from being scheduled with crew who'd exceed their
duty hours?**
`trg_check_duty_limit`, a `BEFORE INSERT` trigger on `crew_assignment`. It
looks up the crew member's `duty_log.hours_on_duty` for that day, adds the
new flight's scheduled duration, and raises `SIGNAL SQLSTATE '45000'` if the
total would exceed 11 hours — the insert never happens.

**Q: What stops two passengers from being assigned the same seat on the
same flight?**
`trg_no_double_seat`, a `BEFORE INSERT` trigger on `ticket`, which checks
for an existing ticket with the same `flight_id` + `seat_no` on a
`CONFIRMED` booking and signals an error if one exists.

**Q: How does one delay reach flights on other aircraft and at other
airports?**
Each pass of `simulate_delay()` calls `compute_cascade_candidates()`, which
evaluates four rules against the current estimated times and writes the
delay each flight *requires* into `cascade_candidate`:
- **AIRCRAFT** — `LAG()` over flights partitioned by aircraft: a leg can't
  leave before the previous leg lands + the airport's turnaround time.
- **CREW** — `LAG()` over each crew member's assignments: a flight can't
  leave before its crew's previous flight lands + 45 min. The seed rosters
  some crew onto a second aircraft mid-day, so this is how a delay jumps
  between aircraft.
- **GATE** — `LAG()` over flights partitioned by gate: boarding can't start
  until the previous flight at that gate has left + 10 min.
- **SLOT** — `ROW_NUMBER()` over departures per airport per clock hour:
  delayed flights beyond `runway_slots_per_hour` move to the next hour.
The largest requirement per flight wins (another `ROW_NUMBER()`), is logged
to `delay_impact` with the cause flight and link type, and is applied. The
next pass re-evaluates with the new times, so a chain can hop aircraft →
crew → gate → slot as far as it needs to.

**Q: How are passengers affected if flights don't wait for them?**
`v_missed_connections` joins each booking's two tickets and compares the
onward flight's ETD with the inbound flight's ETA against the connecting
airport's `min_connect_min`. It's a view, so it's always current: file a
delay and the missed connections appear; reset and they disappear.

**Q: Where are the estimated times stored?**
Nowhere — `v_flight_times` computes ETD/ETA as scheduled time +
`delay_minutes`. Storing them would be a second copy of the same fact.

**Q: How do you know the seed data doesn't cause cascades on its own?**
`tests/test_cascade.py` runs `compute_cascade_candidates()` with every delay
at zero and asserts no rule requires any delay, and that all three flag
views are empty. The seed is built to satisfy that: rotations respect
turnaround times, gates are assigned greedily with a 60-min gap, and each
airport's slot limit is set to its actual peak hour.

## Normalization

**Q: Is this schema in 3NF? Any exceptions?**
Yes, with two documented, trigger/procedure-maintained denormalizations
(and `flight_delay` deliberately doesn't store the delay category, which is
reached through `delay_code`):
`flight.delay_minutes` and `duty_log.hours_flown`/`hours_on_duty`. See
`docs/NORMALIZATION.md`.

**Q: Why isn't `passenger.age` a column?**
MySQL 8 won't allow `CURDATE()`/`NOW()` in a generated column expression
(non-deterministic functions aren't allowed there). Age is computed at
query time with `TIMESTAMPDIFF(YEAR, date_of_birth, CURDATE())` instead of
being stored and going stale.

**Q: Why can a `ticket` reference a `flight` independently of `booking`
referencing anything about flights?**
A `booking` is the passenger-facing unit (one PNR); a single booking can
cover multiple flights (e.g. a connection), so each `ticket` — one seat on
one specific flight — needs its own `flight_id`, not just its `booking_id`.

## Application layer

**Q: How does the app talk to the database — an ORM?**
No ORM. `src/db.py` wraps a `mysql-connector-python` connection pool with
three primitives: `query()` (SELECT, returns dicts), `execute()`
(INSERT/UPDATE/DELETE, returns `lastrowid`), and `call_proc()`/
`call_proc_with_out()` for stored procedures. Each `src/services/*.py`
module owns the actual SQL for one part of the domain; routes only call
services, never write SQL directly.

**Q: How do trigger/procedure errors (like the duty-hour limit) surface to
the user?**
`src/routes/helpers.py::db_action` is a context manager every mutating route
uses; it catches `mysql.connector.Error` (which is what a `SIGNAL
SQLSTATE '45000'` becomes on the Python side) and turns it into a flashed
message instead of a 500 page.

**Q: Why does `/admin` use one generic CRUD implementation for eight
different tables instead of eight separate ones?**
Airports, gates, aircraft types, delay reasons, IATA delay codes, routes,
aircraft, and maintenance logs are all simple reference data with the same shape of interaction
(list/create/edit/delete, no special business rules beyond FK constraints).
`src/services/admin.py::ENTITIES` is a config dict (table, PK, field
list/types) that one set of routes and two templates render generically —
avoiding eight near-identical CRUD modules for tables that don't need
bespoke logic. Flights, crew, passengers, and bookings *do* have bespoke
logic (cascade linkage, certifications, duty limits, the booking
procedure), so those get dedicated blueprints instead.

## Manual changes during the viva

**Q: If I change a table directly in MySQL, does the website show it?**
Yes, on the next page load. Nothing is cached; every page queries MySQL, and the
connection pool resets each session when a connection is returned, so no old
snapshot is reused. New columns appear in each record's "All columns" section
(read with `SELECT *`) and in the admin forms. New ENUM values appear in every
dropdown, because the options are read from `information_schema`. New tables and
views are listed on the Schema page with a row browser, and row counts there are
exact `COUNT(*)`, not InnoDB's cached estimate. `tests/test_live_changes.py`
checks all of this.

**Q: What if I rename or drop a column the app uses?**
Pages that read `SELECT *` just show the new structure. A page whose query names
the old column shows an error page with MySQL's exact message and error number,
not a crash.

**Q: What if I insert a delay into `flight_delay` directly?**
It's recorded, but nothing moves: the cascade runs only through
`simulate_delay()`, which also keeps `flight.delay_minutes` in step. Updating
`flight.delay_minutes` directly does show everywhere at once, because ETD/ETA
are computed from it by `v_flight_times`.
````

### A.107 `docs/design-reference/DESIGN.md`

````markdown
# Your workplace has the answer. Just ask Dala for it. — Style Reference
> constellation floating on black velvet

**Theme:** dark

Source measurements are normalized; roles and recommendations are interpreted. Font summary lists are independent, not paired by position. HTML examples are reconstructions, not source components.

Dala operates as a dark-stage environment where black voids meet a single vivid violet accent, punctuated by amber sparks. Typography is monolithic and weightless — PPNeueMontreal at weight 400 dominates every heading at outsized scales (78–113px) with aggressive negative tracking, so headlines feel sculptural rather than informational. The visual centerpiece is a constellation of tiny multicolored triangular particles forming an organic brain shape, which acts as the brand's signature gesture: knowledge visualized as distributed intelligence rather than hierarchical data. Layout follows a spacious two-column rhythm — oversized left-aligned headlines paired with generous body copy, floating on pure black with no panels, borders, or cards. Components are intentionally reduced to their most essential form: one violet pill button, ghost text links, and large-format text blocks.

## Tokens — Colors

| Name | Value | Token | Role |
|------|-------|-------|------|
| Void | `#000000` | `--color-void` | Page canvas, section backgrounds, negative space — pure black is the dominant surface, not dark gray, creating the void that lets chromatic accents float |
| Bone White | `#ffffff` | `--color-bone-white` | Headlines, body text, icon fills, nav active state — the only typographic color, carrying maximum hierarchy on black |
| Ash Gray | `#9a9a9a` | `--color-ash-gray` | Muted nav text, ghost link color, secondary labels — recedes behind primary text without going invisible |
| Silver Mist | `#bdbdbd` | `--color-silver-mist` | Tertiary body text, caption-level information — the quietest readable gray, for supporting context |
| Electric Iris | `#8052ff` | `--color-electric-iris` | Primary action buttons, logo mark, brand accents — the single saturated violet that signals interactivity and brand identity against the black void |
| Saffron Spark | `#ffb829` | `--color-saffron-spark` | Highlight emphasis text, accent links, attention punctuation — warm yellow against violet creates the brand's chromatic tension |
| Deep Verdant | `#15846e` | `--color-deep-verdant` | Secondary surface tint, logo gradient stop — appears as the deeper end of the brand gradient and in subtle accent washes |

## Tokens — Typography

### PPNeueMontreal — Single typeface across all UI contexts. Display sizes (78–113px) carry headlines at weight 400 with -0.04em tracking — the same weight as body text but massive scale creates hierarchy. Weight 200 (ultra-light) is reserved for 18px body copy, a signature choice: most AI/SaaS sites use 400 for body, but Dala strips weight to make paragraphs feel airy and non-aggressive. Weight 600 at 14px with 0.025em tracking and uppercase serves nav and small labels. The number 400 doing both 113px display and 15px body is unusual — it means the brand trusts scale, not weight, for hierarchy. · `--font-ppneuemontreal`
- **Substitute:** Inter
- **Weights:** 200, 400, 600, 700
- **Sizes:** 12, 14, 15, 18, 24, 27, 36, 42, 48, 78, 113px
- **Line height:** 0.81, 0.90, 1.00, 1.10, 1.20, 1.25, 1.30, 1.50
- **Letter spacing:** -4.52px at 113px, -3.12px at 78px, -1.68px at 42px, -0.48px at 24px, normal at 18px body; 0.025em at 14px uppercase nav
- **OpenType features:** `"ss01" on`
- **Role:** Single typeface across all UI contexts. Display sizes (78–113px) carry headlines at weight 400 with -0.04em tracking — the same weight as body text but massive scale creates hierarchy. Weight 200 (ultra-light) is reserved for 18px body copy, a signature choice: most AI/SaaS sites use 400 for body, but Dala strips weight to make paragraphs feel airy and non-aggressive. Weight 600 at 14px with 0.025em tracking and uppercase serves nav and small labels. The number 400 doing both 113px display and 15px body is unusual — it means the brand trusts scale, not weight, for hierarchy.

### Type Scale

| Role | Family | Weight | Size | Line Height | Letter Spacing | Token |
|------|--------|--------|------|-------------|----------------|-------|
| caption | — | — | 12px | 1.5 | — | `--text-caption` |
| nav-label | — | — | 14px | 1.2 | 0.35px | `--text-nav-label` |
| body | — | — | 18px | 1.5 | — | `--text-body` |
| heading-2xs | — | — | 24px | 1.25 | -0.48px | `--text-heading-2xs` |
| heading-xs | — | — | 27px | 1 | — | `--text-heading-xs` |
| subheading | — | — | 36px | 1.2 | — | `--text-subheading` |
| heading-sm | — | — | 42px | 1.2 | -1.68px | `--text-heading-sm` |
| heading | — | — | 48px | 1.1 | -1.68px | `--text-heading` |
| heading-lg | — | — | 78px | 1.1 | -3.12px | `--text-heading-lg` |
| display | — | — | 113px | 1.1 | -4.52px | `--text-display` |

## Tokens — Spacing & Shapes

**Base unit:** 6px

**Density:** comfortable

### Spacing Scale

| Name | Value | Token |
|------|-------|-------|
| 6 | 6px | `--spacing-6` |
| 12 | 12px | `--spacing-12` |
| 18 | 18px | `--spacing-18` |
| 24 | 24px | `--spacing-24` |
| 30 | 30px | `--spacing-30` |
| 36 | 36px | `--spacing-36` |
| 60 | 60px | `--spacing-60` |
| 96 | 96px | `--spacing-96` |
| 120 | 120px | `--spacing-120` |

### Border Radius

| Element | Value |
|---------|-------|
| nav | 24px |
| tags | 9999px |
| cards | 24px |
| buttons | 24px |

### Layout

- **Page max-width:** 1280px
- **Section gap:** 60-120px
- **Card padding:** 24-38px
- **Element gap:** 6-18px

## Components

### Primary Action Button
**Role:** Filled violet pill, the sole interactive CTA

Background #8052ff (Electric Iris), white text, 22.5px border-radius (pill), 14.4px vertical padding × 15.96px horizontal padding. PPNeueMontreal 14px weight 400 or 600, uppercase with 0.025em tracking. The high radius (22.5px on ~45px height) creates a full pill shape — soft, friendly, unmistakable as the primary action.

### Ghost Text Button
**Role:** Underlined or bare text link, secondary action

No background, no border, color #ffffff or #9a9a9a. PPNeueMontreal 14px weight 400. Used for nav items and inline links. The absence of any container means visual hierarchy comes entirely from type weight and tracking.

### Logo Lockup
**Role:** Brand mark + wordmark in header

Small triangular icon in #8052ff (violet) with a gradient fade through #15846 (teal), paired with 'Dala' wordmark in white. The icon is a stylized angular fragment — geometric, sharp-edged, echoing the triangular particles in the hero visualization.

### Team Member Card
**Role:** Portrait + name + role display

No background, no border, no shadow. Large rounded-rectangle portrait photo (~24px corner radius) with role label in 12px uppercase #8052ff and name in large white display type below. Social icons (Twitter, LinkedIn) appear as small inline glyphs. Cards float on the black canvas with only whitespace separation.

### Carousel Navigation Dot
**Role:** Indicator for slide position in team/investor carousels

Small filled circle ~8px diameter, #8052ff violet for active state. Inactive dots are dimmer or omitted. Padding is minimal — sits directly in the content flow without a container.

### Hero Constellation Visualization
**Role:** Signature brand imagery — brain-shape particle cloud

Thousands of tiny triangular glyphs (outlined, 1-2px) in a full spectrum of vivid colors (violet, amber, teal, magenta, blue) forming an organic brain or cloud shape against pure black. Individual particles are scattered/ambient across the surrounding space as well. This is the site's defining visual — not a static image but an animated field of point-lights.

### Section Headline Block
**Role:** Oversized left-aligned headline + supporting copy

Two-column asymmetric layout: headline at 78–113px weight 400 PPNeueMontreal in white with -0.04em tracking, occupying left half. Body copy at 18px weight 200 (ultra-light) in white or silver, with a small uppercase label (#ffb829 amber) above the body. No boxes, no borders — pure typographic composition on black.

### Navigation Bar
**Role:** Top-aligned site navigation

Transparent background sitting directly on black canvas. Logo left, nav links center/right (Manifesto, Team, Blog) in 14px uppercase PPNeueMontreal with 0.025em tracking. Active or hover state: white. Inactive: #9a9a9a. Request Access button (filled violet pill) anchors the right edge. No border, no backdrop blur on the nav itself.

### Ambient Particle Field
**Role:** Decorative scattered triangle glyphs

Small outlined triangles in various chromatic colors (#8052ff violet, #ffb829 amber, #15846 teal, plus assorted purples and blues) scattered at low opacity across the background outside the main constellation. Creates atmospheric depth without competing with the central visualization.

## Do's and Don'ts

### Do
- Use #8052ff (Electric Iris) exclusively for filled action buttons — no other saturated color should appear as a button background
- Set every headline at weight 400, never bold — Dala achieves hierarchy through scale (78–113px) and tracking (-0.04em), not font weight
- Use PPNeueMontreal weight 200 for 18px body text — the ultra-light weight is a signature, do not substitute weight 400
- Maintain pure #000000 black as every section background — never use dark gray panels or card surfaces; the void is the design
- Apply -0.04em letter-spacing on all display sizes 42px and above, converting to approximately -4.52px at 113px
- Use 24px border-radius for buttons, cards, and nav elements as the consistent radius token — pill shapes only at very small sizes
- Let the particle constellation be the only hero imagery — do not introduce photography, illustrations, or product screenshots into the hero region

### Don't
- Do not use filled violet (#8052ff) for large background blocks or full sections — it is a button and accent color, not a surface
- Do not set body text at weight 400 — Dala's signature ultra-light (200) body copy is what distinguishes the reading experience
- Do not introduce card containers with borders, shadows, or background fills — elements float on black with whitespace alone
- Do not use color #0000ee (default browser link blue) — never specify it; use #ffb829 amber or #ffffff for links
- Do not add gradients to UI components — Dala's palette is flat; gradients belong only in the logo and the particle visualization
- Do not use system fonts as substitutes when PPNeueMontreal-equivalent geometry matters — use Inter as fallback but preserve the weight 200 body and weight 400 headline convention
- Do not place multiple filled buttons in proximity — the violet pill is reserved for singular primary actions per view

## Surfaces

| Level | Name | Value | Purpose |
|-------|------|-------|---------|
| 0 | Void Canvas | `#000000` | Full-page background, all section backgrounds, the base void |
| 1 | Deep Verdant Tint | `#15846` | Subtle accent surface for brand gradient and logo depth |
| 2 | Electric Iris | `#8052ff` | Highest surface — filled buttons, active interactive elements only |

## Elevation

Dala uses no shadows or elevation. All hierarchy is achieved through scale, color contrast, and whitespace on a flat black canvas. The absence of cards-with-shadows is deliberate — the void is the design, and any shadow would break the floating-in-space quality of the typography and particle constellation.

## Imagery

Imagery is entirely procedural and abstract — no photography except team portraits. The signature visual is a dense cloud of thousands of tiny outlined triangular particles in a full vivid spectrum (violets, ambers, teals, magentas, blues) forming an organic brain/neural shape. This particle field is animated and acts as both hero art and brand identity. Surrounding ambient particles drift at lower density across the page background. Triangles are outlined, 1–2px stroke, sharp-edged, in saturated chromatic colors — never grayscale. Team portraits appear as large rounded-rectangle crops (24px radius) without frames or overlays. No product screenshots, no lifestyle photography, no 3D renders — the particle system IS the visual brand.

## Layout

Full-bleed sections on pure black canvas, max content width ~1280px centered. Hero is a two-column asymmetric split: oversized left-aligned headline (113px) with body copy and CTA on the left half, particle brain visualization occupying the right half at massive scale. Subsequent sections alternate the two-column composition (visual-left/text-right, then text-left/visual-right) creating a zigzag reading rhythm. Section gaps are generous (60–120px vertical). No card grids, no pricing tables, no multi-column feature blocks — content lives in spacious two-column text+visual arrangements. Navigation is a minimal transparent top bar, no sidebar, no mega-menu. Density is extremely spacious — one or two elements per viewport, never information-dense.

## Agent Prompt Guide

## Quick Color Reference
- Text: #ffffff (primary), #9a9a9a (secondary), #bdbdbd (tertiary)
- Background: #000000 (canvas only)
- Border: none — Dala uses no visible borders or dividers
- Accent: #ffb829 (Saffron Spark) for emphasis highlights
- primary action: #8052ff (filled action)

## Example Component Prompts

1. **Hero Section**: Full-bleed #000000 canvas. Two-column split. Left: headline at 78px PPNeueMontreal weight 400, #ffffff, letter-spacing -3.12px, reading 'Unlock collective wisdom.' Body copy at 18px weight 200 PPNeueMontreal, #ffffff, max-width 480px. Above body, a small uppercase label at 14px weight 600, #ffb829 amber, letter-spacing 0.35px. Below body, a filled violet pill button: #8052ff background, white text, 14px weight 600 uppercase, 22.5px border-radius, 14.4px vertical padding × 16px horizontal padding. Right: large particle constellation visualization (thousands of tiny colored triangles forming a brain shape).

2. **Section Headline + Body**: #000000 background. Left-aligned headline at 42px PPNeueMontreal weight 400, #ffffff, letter-spacing -1.68px. Supporting body text at 18px weight 200 PPNeueMontreal, #bdbdbd, max-width 520px. No boxes, no borders, no cards — text floats on void.

3. **Navigation Bar**: Transparent background on black. Left: small violet (#8052ff) triangular logo icon + 'Dala' wordmark in #ffffff 14px. Right: nav links 'Manifesto', 'Team', 'Blog' in 14px PPNeueMontreal weight 600, uppercase, 0.025em letter-spacing, color #9a9a9a (inactive) or #ffffff (active). Far right: filled violet pill 'Request Access' button — #8052ff background, white text, 22.5px radius, 14px weight 600 uppercase.

4. **Team Card**: No background, no border. Large portrait photo with 24px border-radius. Above name: role label 'CO FOUNDER & CTO' at 12px PPNeueMontreal weight 400, #8052ff, uppercase. Below photo: name 'Joel Kang' at 27px PPNeueMontreal weight 400, #ffffff. Social icons inline as small glyphs in #9a9a9a.

5. **Carousel Indicator**: Two small dots ~8px, filled #8052ff for active position, no background or border around the dot container. Sits centered below carousel content with 30px gap.

## Similar Brands

- **Linear** — Same dark-void aesthetic with oversized weight-400 display type, generous whitespace, and a single saturated accent (violet/blue) reserved for action — both treat black as an active design material rather than a fallback
- **Vercel** — Identical pattern: pure black canvas, geometric minimalism, single brand color, weight-400 typography at massive display sizes with aggressive negative tracking — both make black the hero
- **Anthropic** — Dark mode-first philosophy with serif-free geometric sans, restrained color palette where one accent dominates, and a typographic system that trusts scale over weight for hierarchy
- **Runway** — Dark void aesthetic with particle/constellation-style generative visuals as brand identity, combined with ultra-light body type and single vivid accent color for CTAs

## Quick Start

### CSS Custom Properties

```css
:root {
  /* Colors */
  --color-void: #000000;
  --color-bone-white: #ffffff;
  --color-ash-gray: #9a9a9a;
  --color-silver-mist: #bdbdbd;
  --color-electric-iris: #8052ff;
  --color-saffron-spark: #ffb829;
  --color-deep-verdant: #15846e;

  /* Typography — Font Families */
  --font-ppneuemontreal: 'PPNeueMontreal', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;

  /* Typography — Scale */
  --text-caption: 12px;
  --leading-caption: 1.5;
  --text-nav-label: 14px;
  --leading-nav-label: 1.2;
  --tracking-nav-label: 0.35px;
  --text-body: 18px;
  --leading-body: 1.5;
  --text-heading-2xs: 24px;
  --leading-heading-2xs: 1.25;
  --tracking-heading-2xs: -0.48px;
  --text-heading-xs: 27px;
  --leading-heading-xs: 1;
  --text-subheading: 36px;
  --leading-subheading: 1.2;
  --text-heading-sm: 42px;
  --leading-heading-sm: 1.2;
  --tracking-heading-sm: -1.68px;
  --text-heading: 48px;
  --leading-heading: 1.1;
  --tracking-heading: -1.68px;
  --text-heading-lg: 78px;
  --leading-heading-lg: 1.1;
  --tracking-heading-lg: -3.12px;
  --text-display: 113px;
  --leading-display: 1.1;
  --tracking-display: -4.52px;

  /* Typography — Weights */
  --font-weight-extralight: 200;
  --font-weight-regular: 400;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;

  /* Spacing */
  --spacing-unit: 6px;
  --spacing-6: 6px;
  --spacing-12: 12px;
  --spacing-18: 18px;
  --spacing-24: 24px;
  --spacing-30: 30px;
  --spacing-36: 36px;
  --spacing-60: 60px;
  --spacing-96: 96px;
  --spacing-120: 120px;

  /* Layout */
  --page-max-width: 1280px;
  --section-gap: 60-120px;
  --card-padding: 24-38px;
  --element-gap: 6-18px;

  /* Border Radius */
  --radius-3xl: 24px;
  --radius-full: 9999px;

  /* Named Radii */
  --radius-nav: 24px;
  --radius-tags: 9999px;
  --radius-cards: 24px;
  --radius-buttons: 24px;

  /* Surfaces */
  --surface-void-canvas: #000000;
  --surface-deep-verdant-tint: #15846;
  --surface-electric-iris: #8052ff;
}
```

### Tailwind v4

```css
@theme {
  /* Colors */
  --color-void: #000000;
  --color-bone-white: #ffffff;
  --color-ash-gray: #9a9a9a;
  --color-silver-mist: #bdbdbd;
  --color-electric-iris: #8052ff;
  --color-saffron-spark: #ffb829;
  --color-deep-verdant: #15846e;

  /* Typography */
  --font-ppneuemontreal: 'PPNeueMontreal', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;

  /* Typography — Scale */
  --text-caption: 12px;
  --leading-caption: 1.5;
  --text-nav-label: 14px;
  --leading-nav-label: 1.2;
  --tracking-nav-label: 0.35px;
  --text-body: 18px;
  --leading-body: 1.5;
  --text-heading-2xs: 24px;
  --leading-heading-2xs: 1.25;
  --tracking-heading-2xs: -0.48px;
  --text-heading-xs: 27px;
  --leading-heading-xs: 1;
  --text-subheading: 36px;
  --leading-subheading: 1.2;
  --text-heading-sm: 42px;
  --leading-heading-sm: 1.2;
  --tracking-heading-sm: -1.68px;
  --text-heading: 48px;
  --leading-heading: 1.1;
  --tracking-heading: -1.68px;
  --text-heading-lg: 78px;
  --leading-heading-lg: 1.1;
  --tracking-heading-lg: -3.12px;
  --text-display: 113px;
  --leading-display: 1.1;
  --tracking-display: -4.52px;

  /* Spacing */
  --spacing-6: 6px;
  --spacing-12: 12px;
  --spacing-18: 18px;
  --spacing-24: 24px;
  --spacing-30: 30px;
  --spacing-36: 36px;
  --spacing-60: 60px;
  --spacing-96: 96px;
  --spacing-120: 120px;

  /* Border Radius */
  --radius-3xl: 24px;
  --radius-full: 9999px;
}
```
````

### A.108 `docs/superpowers/specs/2026-09-23-org-wide-delay-cascade-design.md`

````markdown
# Organisation-wide delay cascade — design

Date: 2026-09-23 · Status: implemented

Changes made while building (all reflected in the code and docs):
- `flight_delay.reason_id` was dropped; the category is reached through
  `delay_code` (a stored copy would be a transitive dependency, breaking 3NF).
- Crew is 400, not 120: 40 aircraft need 100 four-person teams at 2 legs each.
- `v_duty_breaches` measures first ETD to last ETA against 13 h (block hours
  alone never change with a delay, so they couldn't flag anything).
- Rule evaluation is its own procedure, `compute_cascade_candidates()`, so
  the test can check the zero-delay schedule directly.
- Resolving a notice is a plain `UPDATE` from the app, not a procedure.
- Delays can't be filed on ARRIVED/CANCELLED/DIVERTED flights.

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
````
