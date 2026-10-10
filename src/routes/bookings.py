from flask import Blueprint, render_template, request, redirect, url_for, flash
import mysql.connector

from src.routes.helpers import db_action
from src.services import bookings as bookings_service
from src.services import passengers as passengers_service
from src.services import flights as flights_service
from src.services import operations
from src.services import schema_info

bp = Blueprint("bookings", __name__)


@bp.route("/")
def list_view():
    status = request.args.get("status") or None
    return render_template(
        "bookings/list.html", bookings=bookings_service.list_bookings(status=status), status=status
    )


@bp.route("/<int:booking_id>")
def detail(booking_id):
    booking = bookings_service.get_booking(booking_id)
    if not booking:
        flash("Booking not found", "error")
        return redirect(url_for("bookings.list_view"))
    return render_template(
        "bookings/detail.html",
        booking=booking,
        tickets=bookings_service.tickets_for_booking(booking_id),
        flights=flights_service.list_flights(status="SCHEDULED"),
        rebookings=operations.rebookings_for_booking(booking_id),
        record=schema_info.record("booking", "booking_id", booking_id),
    )


@bp.route("/new", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        try:
            booking_id = bookings_service.book_ticket(
                request.form["passenger_id"],
                request.form["flight_id"],
                request.form["seat_no"],
                request.form["ticket_class"],
                request.form["fare"],
            )
            flash("Booking and ticket created", "success")
            return redirect(url_for("bookings.detail", booking_id=booking_id))
        except mysql.connector.Error as e:
            flash(f"Could not create booking: {e.msg}", "error")
    return render_template(
        "bookings/form.html",
        passengers=passengers_service.list_passengers(),
        flights=flights_service.list_flights(),
    )


@bp.route("/<int:booking_id>/cancel", methods=["POST"])
def cancel(booking_id):
    with db_action("Booking cancelled"):
        bookings_service.cancel_booking(booking_id)
    return redirect(url_for("bookings.detail", booking_id=booking_id))


@bp.route("/<int:booking_id>/ticket", methods=["POST"])
def add_ticket(booking_id):
    with db_action("Ticket added"):
        bookings_service.add_ticket(
            booking_id,
            request.form["flight_id"],
            request.form["seat_no"],
            request.form["ticket_class"],
            request.form["fare"],
        )
    return redirect(url_for("bookings.detail", booking_id=booking_id))


@bp.route("/ticket/<int:ticket_id>/checkin", methods=["POST"])
def checkin(ticket_id):
    booking_id = request.form["booking_id"]
    with db_action("Checked in"):
        bookings_service.check_in_ticket(ticket_id)
    return redirect(url_for("bookings.detail", booking_id=booking_id))


@bp.route("/ticket/<int:ticket_id>/rebook", methods=["POST"])
def rebook(ticket_id):
    booking_id = request.form["booking_id"]
    reason = request.form.get("reason", "PASSENGER_REQUEST")
    if reason not in operations.REBOOK_REASONS:
        reason = "PASSENGER_REQUEST"
    with db_action("Ticket moved to the next available flight on the same route"):
        operations.rebook_ticket(ticket_id, reason)
    return redirect(url_for("bookings.detail", booking_id=booking_id))
