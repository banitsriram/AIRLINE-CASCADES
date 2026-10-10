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

The same restriction applies to `rebooking`: `old_flight_id <> new_flight_id`
can't be a CHECK because both columns carry FK actions. Its only writer,
`rebook_ticket()`, always selects a flight other than the ticket's current one.

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
