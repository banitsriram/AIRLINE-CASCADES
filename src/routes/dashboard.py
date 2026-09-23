from datetime import date

from flask import Blueprint, render_template, url_for

from src.services import airports as airports_service
from src.services import dashboard as dashboard_service
from src.services import delays as delays_service

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
    )
