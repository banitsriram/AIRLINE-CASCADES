from flask import Blueprint, render_template

from src.services import airports as airports_service
from src.services import dashboard as dashboard_service
from src.services import delays as delays_service

bp = Blueprint("dashboard", __name__)


@bp.route("/")
def index():
    return render_template(
        "dashboard/index.html",
        summary=dashboard_service.summary(),
        recent_delays=dashboard_service.recent_delays(),
        flags=delays_service.network_flags(),
        airports=airports_service.list_airports(),
    )
