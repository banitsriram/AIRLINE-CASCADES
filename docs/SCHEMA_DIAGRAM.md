# Schema diagram (relationship description)

15 tables, organized into 4 dependency layers (as laid out in
`database/01_schema.sql`) — each layer only references tables in layers
above it. The live schema, with column types and keys, is also browsable at
runtime under **Schema** in the app (backed by `information_schema`).

## Layer 1 — no foreign keys

- **`airport`** — `airport_id` PK
- **`aircraft_type`** — `type_id` PK
- **`delay_reason`** — `reason_id` PK

## Layer 2 — reference Layer 1

- **`route`** → `airport` (origin), `airport` (destination)
- **`aircraft`** → `aircraft_type`, `airport` (base)
- **`crew`** → `airport` (base)
- **`passenger`** — no FKs (referenced by `booking`)

## Layer 3 — reference Layer 2

- **`flight`** → `route`, `aircraft`, and **`flight`** itself
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
- **`flight_delay`** → `flight`, `delay_reason`
- **`ticket`** → `booking`, `flight`

## The cascade relationship

`flight.parent_flight_id → flight.flight_id` is the one self-referencing
edge in the schema. It's what `analyse_cascade()`'s recursive CTE walks:
starting from a root flight, it follows every flight whose
`parent_flight_id` points back into the set already visited, one level per
`UNION ALL` iteration, producing the full downstream delay tree.

## Delete behavior at a glance

Most FKs are `ON DELETE RESTRICT` (you can't delete an airport, route,
aircraft, or aircraft type that's still referenced) — appropriate for
reference data. The exceptions:

- `crew_certification`, `duty_log`, `crew_assignment`, `flight_delay` are
  `ON DELETE CASCADE` from their parent (deleting a crew member or flight
  cleans up its dependent rows).
- `maintenance_log` is `ON DELETE CASCADE` from `aircraft`.
- `ticket` is `ON DELETE RESTRICT` from `flight` (a flight with sold tickets
  can't be deleted outright — cancel it instead) but `ON DELETE CASCADE`
  from `booking` (cancelling/deleting a booking removes its tickets).
- `flight.parent_flight_id` is `ON DELETE SET NULL` (deleting an upstream
  flight doesn't delete the downstream ones — it just detaches them from
  the cascade tree).
