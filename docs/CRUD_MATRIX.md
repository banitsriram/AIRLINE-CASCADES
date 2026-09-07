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
| **Airport** | `GET/POST /admin/airport/new` | `GET /admin/airport/` | `GET/POST /admin/airport/<id>/edit` | `POST /admin/airport/<id>/delete` |
| **Aircraft type** | `GET/POST /admin/aircraft_type/new` | `GET /admin/aircraft_type/` | `GET/POST /admin/aircraft_type/<id>/edit` | `POST /admin/aircraft_type/<id>/delete` |
| **Delay reason** | `GET/POST /admin/delay_reason/new` | `GET /admin/delay_reason/` | `GET/POST /admin/delay_reason/<id>/edit` | `POST /admin/delay_reason/<id>/delete` |
| **Route** | `GET/POST /admin/route/new` | `GET /admin/route/` | `GET/POST /admin/route/<id>/edit` | `POST /admin/route/<id>/delete` |
| **Aircraft** | `GET/POST /admin/aircraft/new` | `GET /admin/aircraft/` | `GET/POST /admin/aircraft/<id>/edit` | `POST /admin/aircraft/<id>/delete` |
| **Maintenance log** | `GET/POST /admin/maintenance_log/new` | `GET /admin/maintenance_log/` | `GET/POST /admin/maintenance_log/<id>/edit` | `POST /admin/maintenance_log/<id>/delete` |

## Read-only / system-maintained (no direct CRUD, by design)

- **`flight_delay`** — created only by `simulate_delay()`, viewed on the
  flight detail page. Directly inserting one would leave
  `flight.delay_minutes` (a maintained denormalization) out of sync.
- **`duty_log`** — maintained entirely by `trg_update_duty` and read on the
  crew duty-status report. It has no independent existence outside what
  flights a crew member actually flew.

## Non-CRUD actions (the project's centerpiece)

- **Simulate a delay** — `POST /cascade/<flight_id>/simulate`, calls
  `simulate_delay()`, which iteratively cascades the delay to every
  downstream flight sharing the same aircraft.
- **Trace a cascade** — `GET /cascade/<flight_id>`, calls
  `analyse_cascade()` (recursive CTE) and lists affected passengers.
- **Find replacement crew** — `GET /crew/replacement/<flight_id>`, calls
  `find_replacement_crew()`.
