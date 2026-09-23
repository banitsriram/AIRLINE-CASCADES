from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for, flash

from src.services import airports as airports_service

bp = Blueprint("airports", __name__)


@bp.route("/")
def list_view():
    return render_template("airports/list.html", airports=airports_service.list_airports())


@bp.route("/<int:airport_id>/board")
def board(airport_id):
    airport = airports_service.get_airport(airport_id)
    if not airport:
        flash("Airport not found", "error")
        return redirect(url_for("airports.list_view"))
    day = request.args.get("date") or date.today().isoformat()
    return render_template(
        "airports/board.html",
        airport=airport,
        day=day,
        dates=airports_service.board_dates(),
        departures=airports_service.departures(airport_id, day),
        arrivals=airports_service.arrivals(airport_id, day),
    )
