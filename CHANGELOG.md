# Changelog

## 1.0.0

First public release.

### Engine
- Delay cascade across aircraft rotations, crew connections, gate
  occupancy and runway slots, as an iterative stored procedure that logs
  every change with its cause and pass.
- Each pass is limited to the window of the schedule the delay can reach,
  so cost follows the size of the disruption rather than the schedule
  (a 28-day schedule: 6.5 s to 0.5 s for the same delay).
- Operations clock: flights board, depart and land at their estimated
  times; crew duty hours accrue by trigger; notices close and journeys
  complete.
- Rebooking of broken connections onto the next makeable flight with a free
  seat, logged in `rebooking`.

### App
- Pages for flights, delays and their impact, airport boards, cascade
  traces, crew, passengers, bookings, reports, reference data and a live
  schema browser.
- JSON API under `/api/v1` ([docs/API.md](docs/API.md)).
- CSRF protection on all forms; JSON-only API writes.

### Data
- Seeded hub-and-spoke airline: 20 airports, 40 aircraft, 400 crew, and a
  schedule of any length (`SEED_DAYS`, default 7: 1,400 flights, 2,000
  passengers, ~15,000 tickets).

### Project
- pytest suite, Docker Compose setup, GitHub Actions CI.
