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
