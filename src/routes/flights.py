from flask import Blueprint, render_template, request, redirect, url_for, flash

from src.routes.helpers import db_action
from src.services import flights as flights_service
from src.services import lookups

bp = Blueprint("flights", __name__)


@bp.route("/")
def list_view():
    status = request.args.get("status") or None
    date = request.args.get("date") or None
    rows = flights_service.list_flights(status=status, date=date)
    return render_template("flights/list.html", flights=rows, status=status, date=date)


@bp.route("/<int:flight_id>")
def detail(flight_id):
    flight = flights_service.get_flight(flight_id)
    if not flight:
        flash("Flight not found", "error")
        return redirect(url_for("flights.list_view"))
    return render_template(
        "flights/detail.html",
        flight=flight,
        crew=flights_service.crew_for_flight(flight_id),
        delays=flights_service.delays_for_flight(flight_id),
        all_crew=lookups.crew(),
    )


@bp.route("/new", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        with db_action("Flight created"):
            flights_service.create_flight(request.form)
        return redirect(url_for("flights.list_view"))
    return render_template(
        "flights/form.html", flight=None, routes=lookups.routes(), aircraft=lookups.aircraft()
    )


@bp.route("/<int:flight_id>/edit", methods=["GET", "POST"])
def edit(flight_id):
    flight = flights_service.get_flight(flight_id)
    if not flight:
        flash("Flight not found", "error")
        return redirect(url_for("flights.list_view"))
    if request.method == "POST":
        with db_action("Flight updated"):
            flights_service.update_flight(flight_id, request.form)
        return redirect(url_for("flights.detail", flight_id=flight_id))
    return render_template(
        "flights/form.html", flight=flight, routes=lookups.routes(), aircraft=lookups.aircraft()
    )


@bp.route("/<int:flight_id>/delete", methods=["POST"])
def delete(flight_id):
    with db_action("Flight deleted"):
        flights_service.delete_flight(flight_id)
    return redirect(url_for("flights.list_view"))


@bp.route("/<int:flight_id>/assign-crew", methods=["POST"])
def assign_crew(flight_id):
    with db_action("Crew assigned"):
        flights_service.assign_crew(flight_id, request.form["crew_id"], request.form["role"])
    return redirect(url_for("flights.detail", flight_id=flight_id))


@bp.route("/<int:flight_id>/unassign-crew/<int:crew_id>", methods=["POST"])
def unassign_crew(flight_id, crew_id):
    with db_action("Crew unassigned"):
        flights_service.unassign_crew(flight_id, crew_id)
    return redirect(url_for("flights.detail", flight_id=flight_id))
