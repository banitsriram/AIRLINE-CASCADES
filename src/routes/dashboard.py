from datetime import date, datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for

from src.services import airports as airports_service
from src.services import dashboard as dashboard_service
from src.services import delays as delays_service
from src.services import operations
from src.routes.helpers import db_action

bp = Blueprint("dashboard", __name__)


@bp.route("/")
def index():
    airports = airports_service.list_airports()
    routes = dashboard_service.network_routes()
    network = [
        {"id": a["airport_id"], "iata": a["iata_code"], "city": a["city"],
         "late": a["delayed_departures"], "deps": a["departures_today"],
         "url": url_for("airports.board", airport_id=a["airport_id"])}
        for a in airports
    ]
    return render_template(
        "dashboard/index.html",
        today=date.today(),
        network=network,
        network_routes=[[r["a"], r["b"]] for r in routes],
        summary=dashboard_service.summary(),
        recent_delays=dashboard_service.recent_delays(),
        flags=delays_service.network_flags(),
        airports=airports,
        clock=operations.clock_position(),
        now=datetime.now(),
    )


@bp.route("/clock", methods=["POST"])
def advance_clock():
    try:
        until = datetime.strptime(request.form["until"], "%Y-%m-%dT%H:%M")
    except (KeyError, ValueError):
        flash("Pick a date and time to run the operation to", "error")
        return redirect(url_for("dashboard.index"))
    with db_action():
        moved = operations.advance_clock(until)
        flash(
            f"Ran to {until:%a %d %b, %H:%M}: {moved['departed']} departed, {moved['arrived']} landed, "
            f"{moved['boarding']} boarding, {moved['notices_closed']} delay notices closed, "
            f"{moved['bookings_completed']} bookings completed",
            "success",
        )
    return redirect(url_for("dashboard.index"))
