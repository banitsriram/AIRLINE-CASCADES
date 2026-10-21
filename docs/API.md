# JSON API

Everything the web pages can do with flights, delays, airport boards and the
operations clock, as JSON under `/api/v1`. The API calls the same service
functions and stored procedures as the pages, so the cascade, validation and
error messages are identical.

Conventions:

- Times are ISO 8601 local times without a zone (`2026-10-22T05:40:00`),
  as stored in MySQL. `std`/`sta` are scheduled, `etd`/`eta` estimated
  (scheduled + `delay_minutes`).
- Writes take a JSON body and `Content-Type: application/json`; anything
  else gets `415`.
- Errors are `{"error": "...", ...}` with a matching status code.
- There is no authentication. Run it locally or behind your own.

| Method | Path | |
|---|---|---|
| GET | [`/api/v1/flights`](#list-flights) | Flights, filterable by status, date and search |
| GET | [`/api/v1/flights/<id>`](#one-flight) | A flight with its crew, delays and knock-on |
| POST | [`/api/v1/flights/<id>/delays`](#file-a-delay) | File a delay and run the cascade |
| GET | [`/api/v1/delays`](#list-delays) | Delay notices, newest first |
| GET | [`/api/v1/delays/<id>`](#one-delay) | A notice and its full impact |
| GET | [`/api/v1/airports`](#airports) | Airports with today's departures and late counts |
| GET | [`/api/v1/airports/<IATA>/board`](#airport-board) | Departures and arrivals for a day |
| GET | [`/api/v1/network`](#network) | Network-wide flags and the clock position |
| POST | [`/api/v1/clock`](#run-the-clock) | Run the operation forward |

## List flights

`GET /api/v1/flights?status=&date=&q=`

| Parameter | |
|---|---|
| `status` | A flight status (`SCHEDULED`, `BOARDING`, `DEPARTED`, `ARRIVED`, `CANCELLED`, `DIVERTED`), or `DELAYED` for any flight running late |
| `date` | `YYYY-MM-DD`, by scheduled departure |
| `q` | Flight number or registration (substring), or an origin/destination IATA code |

```json
{
  "count": 200,
  "flights": [
    {
      "flight_id": 206,
      "flight_number": "AI-101",
      "origin": "DEL", "dest": "HYD",
      "std": "2026-10-22T05:40:00", "sta": "2026-10-22T07:23:00",
      "etd": "2026-10-22T05:40:00", "eta": "2026-10-22T07:23:00",
      "delay_minutes": 0,
      "status": "SCHEDULED",
      "display_status": "ON TIME",
      "registration": "VT-A01",
      "gate_code": "A4",
      "...": "..."
    }
  ]
}
```

## One flight

`GET /api/v1/flights/<id>`

The flight's fields as above, plus:

```json
{
  "crew": [
    {"crew_id": 1, "name": "Sai Chawla", "role": "CAPTAIN", "assigned_at": "2026-10-21T19:19:12"},
    {"crew_id": 2, "name": "Reyansh Banerjee", "role": "FIRST_OFFICER", "assigned_at": "2026-10-21T19:19:12"}
  ],
  "delays": [],
  "knock_on": []
}
```

`delays` are notices filed on this flight; `knock_on` is delay it received
from other flights' notices, each with the link and causing flight.

## File a delay

`POST /api/v1/flights/<id>/delays`

```bash
curl -X POST localhost:5000/api/v1/flights/206/delays \
  -H 'Content-Type: application/json' \
  -d '{"code": "41", "minutes": 180, "reported_by": "R. Mehta (Duty Manager DEL)",
       "sub_reason": "Hydraulic leak found on walk-around",
       "meal_voucher": true, "compensation_eligible": true}'
```

| Field | | |
|---|---|---|
| `code` or `code_id` | required | IATA delay code (`"41"`) or its `delay_code.code_id` |
| `minutes` or `new_etd` | required | Delay to add, or the new ETD (`YYYY-MM-DDTHH:MM`); `new_etd` wins if both are sent |
| `reported_by` | required | Who filed it |
| `phase` | default `PRE_BOARDING` | `PRE_BOARDING`, `AT_GATE`, `TAXI`, `AIRBORNE` |
| `ops_status` | default `DELAYED` | `DELAYED`, `ON_HOLD`, `CANCELLED` (a cancellation moves nothing downstream) |
| `sub_reason`, `announcement`, `remarks` | optional | Free text |
| `new_gate_id`, `new_boarding_time`, `swap_aircraft_id` | optional | Operational changes made with the notice |
| `pax_deboarded`, `meal_voucher`, `compensation_eligible`, `rebooking_offered` | optional | Booleans |

`201` returns the same body as [one delay](#one-delay).

Errors:

```json
422  {"error": "Invalid delay notice", "details": ["Reported by is required", "Pick an IATA delay code"]}
409  {"error": "Cannot delay a flight that has arrived, diverted or been cancelled"}
415  {"error": "Send a JSON body with Content-Type: application/json"}
```

## List delays

`GET /api/v1/delays?open=1`

`open=1` returns only notices not yet resolved. Each row has the flight,
category and IATA code, minutes, who reported it, and
`knock_on_flights` / `knock_on_minutes`: how many other flights the cascade
moved and by how much in total.

## One delay

`GET /api/v1/delays/<id>`

```json
{
  "notice": {
    "delay_id": 11, "flight_id": 206, "flight_number": "AI-101",
    "origin": "DEL", "dest": "HYD",
    "category": "TECHNICAL", "iata_code": "41", "code_description": "Aircraft defect",
    "minutes": 180, "phase": "PRE_BOARDING", "ops_status": "DELAYED",
    "etd": "2026-10-22T08:40:00", "eta": "2026-10-22T10:23:00",
    "reported_by": "R. Mehta (Duty Manager DEL)", "resolved_at": null,
    "...": "..."
  },
  "impacts": [
    {
      "pass_no": 1, "link": "AIRCRAFT",
      "flight_id": 254, "flight_number": "AI-102", "origin": "HYD", "dest": "DEL",
      "registration": "VT-A01",
      "cause_flight_id": 206, "cause_flight": "AI-101",
      "minutes_added": 165,
      "old_etd": "2026-10-22T08:28:00", "new_etd": "2026-10-22T11:13:00",
      "delay_minutes": 212
    },
    {
      "pass_no": 2, "link": "SLOT",
      "flight_id": 254, "flight_number": "AI-102",
      "cause_flight_id": null, "cause_flight": null,
      "minutes_added": 47,
      "old_etd": "2026-10-22T11:13:00", "new_etd": "2026-10-22T12:00:00",
      "...": "..."
    }
  ],
  "knock_on_flights": 7,
  "knock_on_minutes": 835,
  "passengers_affected": 87,
  "missed_connections": [
    {
      "pnr": "PN09FH", "passenger_name": "Ananya Joshi",
      "in_flight": "AI-101", "in_eta": "2026-10-22T10:23:00",
      "out_flight": "AI-307", "out_etd": "2026-10-22T10:36:00",
      "connect_airport": "HYD", "connect_min": 13, "min_connect_min": 60
    }
  ],
  "duty_breaches": [],
  "curfew_risks": []
}
```

`impacts` has one row per change, so a flight moved in several passes
appears more than once; `knock_on_flights` counts flights. `delay_minutes`
on an impact row is the flight's total delay now, not at that pass.
How the passes work is in [CASCADE_ENGINE.md](CASCADE_ENGINE.md).

## Airports

`GET /api/v1/airports`

Every airport with its operating rules (`open_time`/`close_time` curfew,
`runway_slots_per_hour`, `min_connect_min`, `min_turnaround_min`), gate
count, `departures_today` and `delayed_departures`.

## Airport board

`GET /api/v1/airports/<IATA>/board?date=YYYY-MM-DD`

The airport's row, plus `departures` and `arrivals` for the date (default
today), each a list of flights as in [list flights](#list-flights). The IATA
code is case-insensitive.

## Network

`GET /api/v1/network`

```json
{
  "late_flights": 46,
  "flags": {"missed": 25, "duty": 0, "curfew": 0},
  "clock": "2026-10-21T19:19:00"
}
```

`clock` is the latest actual departure or arrival recorded (`null` before
anything has flown).

## Run the clock

`POST /api/v1/clock`

```bash
curl -X POST localhost:5000/api/v1/clock \
  -H 'Content-Type: application/json' -d '{"until": "2026-10-22T14:00"}'
```

Boards, departs and lands every flight whose boarding time, ETD or ETA is at
or before `until` (default now), books crew duty hours as flights land,
closes notices on flights that have left and completes finished bookings.
It never moves anything backwards, so an earlier `until` changes nothing.
`departed` counts every flight that took off in this run, including those
that also landed in it.

```json
{"until": "2026-10-22T14:00:00", "boarding": 9, "departed": 152, "arrived": 135,
 "notices_closed": 0, "bookings_completed": 1241}
```
