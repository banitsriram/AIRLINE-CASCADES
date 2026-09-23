from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for, flash

from src.routes.helpers import db_action
from src.services import passengers as passengers_service
from src.services import schema_info

bp = Blueprint("passengers", __name__)


def _validate_dob(value):
    if not value:
        return "Date of birth is required"
    if date.fromisoformat(value) >= date.today():
        return "Date of birth must be in the past"
    return None


@bp.route("/")
def list_view():
    search = request.args.get("q") or None
    return render_template(
        "passengers/list.html",
        passengers=passengers_service.list_passengers(search=search),
        search=search,
    )


@bp.route("/<int:passenger_id>")
def detail(passenger_id):
    passenger = passengers_service.get_passenger(passenger_id)
    if not passenger:
        flash("Passenger not found", "error")
        return redirect(url_for("passengers.list_view"))
    return render_template(
        "passengers/detail.html",
        passenger=passenger,
        bookings=passengers_service.bookings_for_passenger(passenger_id),
        record=schema_info.record("passenger", "passenger_id", passenger_id),
    )


@bp.route("/new", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        error = _validate_dob(request.form.get("date_of_birth"))
        if error:
            flash(error, "error")
            return render_template("passengers/form.html", passenger=None)
        with db_action("Passenger created"):
            passengers_service.create_passenger(request.form)
        return redirect(url_for("passengers.list_view"))
    return render_template("passengers/form.html", passenger=None)


@bp.route("/<int:passenger_id>/edit", methods=["GET", "POST"])
def edit(passenger_id):
    passenger = passengers_service.get_passenger(passenger_id)
    if not passenger:
        flash("Passenger not found", "error")
        return redirect(url_for("passengers.list_view"))
    if request.method == "POST":
        error = _validate_dob(request.form.get("date_of_birth"))
        if error:
            flash(error, "error")
            return render_template("passengers/form.html", passenger=passenger)
        with db_action("Passenger updated"):
            passengers_service.update_passenger(passenger_id, request.form)
        return redirect(url_for("passengers.detail", passenger_id=passenger_id))
    return render_template("passengers/form.html", passenger=passenger)


@bp.route("/<int:passenger_id>/delete", methods=["POST"])
def delete(passenger_id):
    with db_action("Passenger deleted"):
        passengers_service.delete_passenger(passenger_id)
    return redirect(url_for("passengers.list_view"))
