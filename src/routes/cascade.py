from flask import Blueprint, render_template, redirect, url_for, flash

from src.services import cascade as cascade_service
from src.services import flights as flights_service

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
    )
