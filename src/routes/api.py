"""JSON API over the same services the pages use. Read endpoints mirror the
main pages; the two write endpoints file a delay (running the cascade) and
advance the operations clock.

    GET  /api/v1/flights?status=&date=&q=
    GET  /api/v1/flights/<id>
    POST /api/v1/flights/<id>/delays
    GET  /api/v1/delays?open=1
    GET  /api/v1/delays/<id>
    GET  /api/v1/airports
    GET  /api/v1/airports/<IATA>/board?date=YYYY-MM-DD
    GET  /api/v1/network
    POST /api/v1/clock
"""

from datetime import date, datetime

from flask import Blueprint, jsonify, request
import mysql.connector

from src.db import query
from src.routes.delays import notice_from_form
from src.services import airports as airports_service
from src.services import delays as delays_service
from src.services import flights as flights_service
from src.services import operations

bp = Blueprint("api", __name__)


def _error(message, status, **extra):
    return jsonify({"error": message, **extra}), status


@bp.before_request
def _json_only():
    """Writes must be JSON. Besides being the API's contract, this keeps the
    endpoints out of reach of cross-site HTML forms."""
    if request.method == "POST" and not request.is_json:
        return _error("Send a JSON body with Content-Type: application/json", 415)


@bp.errorhandler(404)
def _not_found(_err):
    return _error("Not found", 404)


@bp.errorhandler(mysql.connector.Error)
def _database_error(err):
    return _error(err.msg, 500, mysql_errno=err.errno)


@bp.get("/flights")
def flights():
    rows = flights_service.list_flights(
        status=request.args.get("status") or None,
        date=request.args.get("date") or None,
        q=(request.args.get("q") or "").strip() or None,
    )
    return jsonify({"count": len(rows), "flights": rows})


@bp.get("/flights/<int:flight_id>")
def flight(flight_id):
    row = flights_service.get_flight(flight_id)
    if not row:
        return _error("Flight not found", 404)
    return jsonify({
        **row,
        "crew": flights_service.crew_for_flight(flight_id),
        "delays": flights_service.delays_for_flight(flight_id),
        "knock_on": flights_service.knock_on_for_flight(flight_id),
    })


def _as_form(body):
    """Shapes a JSON delay notice like the HTML form submits it, so both go
    through the same validation: checkboxes are present-or-absent, the IATA
    code is looked up, and numbers become strings."""
    form = {}
    for key, value in body.items():
        if value is None or value is False:
            continue
        form[key] = "on" if value is True else str(value)
    if "code" in form and "code_id" not in form:
        found = query("SELECT code_id FROM delay_code WHERE iata_code = %s", (form["code"],))
        if found:
            form["code_id"] = str(found[0]["code_id"])
    form.setdefault("phase", "PRE_BOARDING")
    form.setdefault("ops_status", "DELAYED")
    return form


@bp.post("/flights/<int:flight_id>/delays")
def file_delay(flight_id):
    row = flights_service.get_flight(flight_id)
    if not row:
        return _error("Flight not found", 404)
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return _error("Send the notice as a JSON object", 400)
    notice, errors = notice_from_form(_as_form(body), row)
    if errors:
        return _error("Invalid delay notice", 422, details=errors)
    try:
        delay_id = delays_service.file_delay(flight_id, notice)
    except mysql.connector.Error as e:
        return _error(e.msg, 409)
    return delay(delay_id)[0], 201


@bp.get("/delays")
def delays():
    rows = delays_service.list_delays(open_only=request.args.get("open") == "1")
    return jsonify({"count": len(rows), "delays": rows})


@bp.get("/delays/<int:delay_id>")
def delay(delay_id):
    notice = delays_service.get_delay(delay_id)
    if not notice:
        return _error("Delay notice not found", 404)
    impacts = delays_service.impacts(delay_id)
    summary = delays_service.affected_summary({notice["flight_id"]} | {i["flight_id"] for i in impacts})
    return jsonify({
        "notice": notice,
        "impacts": impacts,
        "knock_on_flights": len(impacts),
        "knock_on_minutes": sum(i["minutes_added"] for i in impacts),
        "missed_connections": summary["missed"],
        "duty_breaches": summary["duty"],
        "curfew_risks": summary["curfew"],
        "passengers_affected": summary["passengers"],
    }), 200


@bp.get("/airports")
def airports():
    return jsonify({"airports": airports_service.list_airports()})


@bp.get("/airports/<iata>/board")
def board(iata):
    found = query("SELECT airport_id FROM airport WHERE iata_code = %s", (iata.upper(),))
    if not found:
        return _error("Airport not found", 404)
    airport_id = found[0]["airport_id"]
    day = request.args.get("date") or date.today().isoformat()
    return jsonify({
        "airport": airports_service.get_airport(airport_id),
        "date": day,
        "departures": airports_service.departures(airport_id, day),
        "arrivals": airports_service.arrivals(airport_id, day),
    })


@bp.get("/network")
def network():
    return jsonify({
        "flags": delays_service.network_flags(),
        "late_flights": query(
            "SELECT COUNT(*) AS n FROM flight WHERE delay_minutes > 0 AND status IN ('SCHEDULED', 'BOARDING', 'DEPARTED')"
        )[0]["n"],
        "clock": operations.clock_position(),
    })


@bp.post("/clock")
def clock():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        body = {}
    try:
        until = datetime.fromisoformat(body["until"]) if body.get("until") else datetime.now()
    except (TypeError, ValueError):
        return _error("'until' must be an ISO date-time, e.g. 2026-10-12T14:00", 400)
    return jsonify({"until": until, **operations.advance_clock(until)})
