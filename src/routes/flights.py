from flask import Blueprint, render_template, request, redirect, url_for, flash
import mysql.connector

from src.routes.delays import notice_from_form
from src.routes.helpers import db_action
from src.services import delays as delays_service
from src.services import flights as flights_service
from src.services import lookups
from src.services import schema_info

bp = Blueprint("flights", __name__)


@bp.route("/")
def list_view():
    status = request.args.get("status") or None
    date = request.args.get("date") or None
    q = (request.args.get("q") or "").strip() or None
    rows = flights_service.list_flights(status=status, date=date, q=q)
    return render_template("flights/list.html", flights=rows, status=status, date=date, q=q)


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
        knock_on=flights_service.knock_on_for_flight(flight_id),
        all_crew=lookups.crew(),
        record=schema_info.record("flight", "flight_id", flight_id),
    )


@bp.route("/new", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        if not flights_service.gate_matches_route(request.form.get("gate_id"), request.form.get("route_id")):
            flash("The gate must be at the route's departure airport", "error")
            return redirect(request.url)
        with db_action("Flight created"):
            flights_service.create_flight(request.form)
        return redirect(url_for("flights.list_view"))
    return render_template(
        "flights/form.html", flight=None, routes=lookups.routes(), aircraft=lookups.aircraft(),
        gates=lookups.gates(),
    )


@bp.route("/<int:flight_id>/edit", methods=["GET", "POST"])
def edit(flight_id):
    flight = flights_service.get_flight(flight_id)
    if not flight:
        flash("Flight not found", "error")
        return redirect(url_for("flights.list_view"))
    if request.method == "POST":
        if not flights_service.gate_matches_route(request.form.get("gate_id"), request.form.get("route_id")):
            flash("The gate must be at the route's departure airport", "error")
            return redirect(request.url)
        with db_action("Flight updated"):
            flights_service.update_flight(flight_id, request.form)
        return redirect(url_for("flights.detail", flight_id=flight_id))
    return render_template(
        "flights/form.html", flight=flight, routes=lookups.routes(), aircraft=lookups.aircraft(),
        gates=lookups.gates(),
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


@bp.route("/<int:flight_id>/delay", methods=["GET", "POST"])
def delay(flight_id):
    flight = flights_service.get_flight(flight_id)
    if not flight:
        flash("Flight not found", "error")
        return redirect(url_for("flights.list_view"))
    if request.method == "POST":
        notice, errors = notice_from_form(request.form, flight)
        if not errors:
            try:
                delay_id = delays_service.file_delay(flight_id, notice)
                flash(f"Delay filed on {flight['flight_number']} and cascaded across the network", "success")
                return redirect(url_for("delays.detail", delay_id=delay_id))
            except mysql.connector.Error as e:
                errors.append(f"Database error: {e.msg}")
        for e in errors:
            flash(e, "error")
    return render_template(
        "delays/form.html",
        flight=flight,
        values=request.form,
        codes=lookups.delay_codes(),
        gates=lookups.gates(flight["origin_airport_id"]),
        aircraft=lookups.aircraft(),
        phases=lookups.enum_values("flight_delay", "phase"),
        ops_statuses=lookups.enum_values("flight_delay", "ops_status"),
    )
