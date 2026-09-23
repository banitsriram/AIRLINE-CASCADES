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
- `docs/REPORT_CONTEXT.md` — everything needed to write the project report (design, SQL, data, measured results, full source)
- `docs/REPORT_CONTEXT_CORE.md` — the same without the source-code appendix (smaller upload)
