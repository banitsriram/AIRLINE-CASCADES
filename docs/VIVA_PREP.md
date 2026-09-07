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
user's "Simulate Delay" click rather than an UPDATE statement. See
`docs/DEVIATIONS.md` §4.

**Q: How do you know `simulate_delay()`'s loop terminates?**
Each pass only ever *increases* `delay_minutes` on rows it touches (its
`WHERE` clause requires `downstream.delay_minutes <` the new value), and it
only updates a row when that would actually change something. Once a pass
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

## Normalization

**Q: Is this schema in 3NF? Any exceptions?**
Yes, with two documented, trigger/procedure-maintained denormalizations:
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

**Q: Why does `/admin` use one generic CRUD implementation for six
different tables instead of six separate ones?**
Airports, aircraft types, delay reasons, routes, aircraft, and maintenance
logs are all simple reference data with the same shape of interaction
(list/create/edit/delete, no special business rules beyond FK constraints).
`src/services/admin.py::ENTITIES` is a config dict (table, PK, field
list/types) that one set of routes and two templates render generically —
avoiding six near-identical CRUD modules for tables that don't need
bespoke logic. Flights, crew, passengers, and bookings *do* have bespoke
logic (cascade linkage, certifications, duty limits, the booking
procedure), so those get dedicated blueprints instead.
