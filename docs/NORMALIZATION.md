# Normalization

All 15 tables are in 3NF: every non-key attribute depends on the whole
primary key and nothing but the key. Two attributes are deliberately
denormalized, both for performance, and both are maintained exclusively by
triggers/procedures rather than by application code, so they never drift out
of sync with the data they're derived from.

## Per-table 3NF justification

| Table | Key | Notes |
|---|---|---|
| `airport` | `airport_id` | All attributes (IATA/ICAO code, city, country, timezone) describe the airport itself. |
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
| `flight_delay` | `delay_id` | One delay event, with its own reason and duration. |
| `ticket` | `ticket_id` | Seat, fare, class describe one seat on one flight within one booking — a booking can cover several flights (e.g. a connection), so this can't be folded into `booking`. |

## The two documented denormalizations

1. **`flight.delay_minutes`** — the running total delay for a flight. In
   3NF this is derivable by summing `flight_delay.minutes` for the flight,
   but that sum is read on every flight list/detail page and by every
   report, so it's kept as a maintained column instead. It is written in
   exactly one place: `simulate_delay()` (`05_procedures.sql`), which both
   inserts the `flight_delay` row and updates `flight.delay_minutes` in the
   same procedure — there's no path that can update one without the other.

2. **`duty_log.hours_flown` / `duty_log.hours_on_duty`** — running totals of
   a crew member's flown/on-duty hours for a given day. These are derivable
   from `crew_assignment` joined to `flight.actual_departure`/
   `actual_arrival`, but they're checked on every crew assignment
   (`trg_check_duty_limit`, before insert) and read on the duty-status
   report, so recomputing the join each time would be wasteful. They're
   maintained by `trg_update_duty` (`04_triggers.sql`), which fires
   `AFTER UPDATE ON flight` whenever `actual_arrival` is newly set, and
   upserts the day's totals for every crew member assigned to that flight.
