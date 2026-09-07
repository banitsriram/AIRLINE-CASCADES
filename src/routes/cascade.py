from flask import Blueprint, render_template, request, redirect, url_for, flash

from src.routes.helpers import db_action
from src.services import cascade as cascade_service
from src.services import flights as flights_service
from src.services import lookups

bp = Blueprint("cascade", __name__)


@bp.route("/")
def index():
    return render_template("cascade/index.html", flights=flights_service.list_flights())


@bp.route("/<int:flight_id>")
def trace(flight_id):
    flight = flights_service.get_flight(flight_id)
    if not flight:
        flash("Flight not found", "error")
        return redirect(url_for("cascade.index"))
    return render_template(
        "cascade/trace.html",
        flight=flight,
        tree=cascade_service.analyse_cascade(flight_id),
        passengers=cascade_service.affected_passengers(flight_id),
        reasons=lookups.delay_reasons(),
    )


@bp.route("/<int:flight_id>/simulate", methods=["POST"])
def simulate(flight_id):
    with db_action("Delay simulated and cascaded downstream"):
        cascade_service.simulate_delay(
            flight_id, int(request.form["minutes"]), int(request.form["reason_id"])
        )
    return redirect(url_for("cascade.trace", flight_id=flight_id))
