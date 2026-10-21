from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash

from src.routes.helpers import db_action
from src.services import delays as delays_service
from src.services import operations
from src.services.lookups import enum_values
from src.services import schema_info

bp = Blueprint("delays", __name__)

FLAGS = ("pax_deboarded", "meal_voucher", "compensation_eligible", "rebooking_offered")


def _text(form, name):
    return (form.get(name) or "").strip() or None


def _int(form, name):
    value = form.get(name)
    return int(value) if value else None


def _datetime(form, name):
    value = form.get(name)
    return datetime.strptime(value, "%Y-%m-%dT%H:%M") if value else None


def editable_from_form(form):
    """The fields that can still change after a notice is filed."""
    notice = {f: _text(form, f) for f in ("sub_reason", "announcement", "reported_by", "remarks")}
    notice.update({f: f in form for f in FLAGS})
    errors = [] if notice["reported_by"] else ["Reported by is required"]
    return notice, errors


def notice_from_form(form, flight):
    """Validates the delay form. Minutes can be given directly or as a new ETD;
    the ETD wins when both are filled, since it's what the duty manager sees."""
    notice, errors = editable_from_form(form)
    try:
        notice["code_id"] = _int(form, "code_id")
        notice["new_gate_id"] = _int(form, "new_gate_id")
        notice["swap_aircraft_id"] = _int(form, "swap_aircraft_id")
        notice["new_boarding_time"] = _datetime(form, "new_boarding_time")
        new_etd = _datetime(form, "new_etd")
        if new_etd:
            notice["minutes"] = int((new_etd - flight["etd"]).total_seconds() // 60)
        else:
            notice["minutes"] = _int(form, "minutes") or 0
    except ValueError:
        return notice, errors + ["Minutes, times and selections must be valid values"]

    notice["phase"] = form.get("phase")
    notice["ops_status"] = form.get("ops_status")
    if notice["phase"] not in enum_values("flight_delay", "phase"):
        errors.append("Pick a delay phase")
    if notice["ops_status"] not in enum_values("flight_delay", "ops_status"):
        errors.append("Pick an operational status")
    if not notice["code_id"]:
        errors.append("Pick an IATA delay code")
    if notice["minutes"] < 0:
        errors.append("The new departure time can't be earlier than the current estimate")
    elif notice["minutes"] == 0 and notice["ops_status"] == "DELAYED":
        errors.append("A delay needs at least 1 minute (use ON HOLD or CANCELLED otherwise)")
    if notice["minutes"] > 24 * 60:
        errors.append("Delays over 24 hours should be filed as a cancellation")
    return notice, errors


@bp.route("/")
def list_view():
    open_only = request.args.get("open") == "1"
    return render_template(
        "delays/list.html", delays=delays_service.list_delays(open_only=open_only), open_only=open_only
    )


@bp.route("/<int:delay_id>")
def detail(delay_id):
    notice = delays_service.get_delay(delay_id)
    if not notice:
        flash("Delay notice not found", "error")
        return redirect(url_for("delays.list_view"))
    impacts = delays_service.impacts(delay_id)
    affected = {notice["flight_id"]} | {i["flight_id"] for i in impacts}
    by_link = {}
    for i in impacts:
        by_link[i["link"]] = by_link.get(i["link"], 0) + 1
    return render_template(
        "delays/detail.html",
        notice=notice,
        impacts=impacts,
        by_link=by_link,
        knock_on_minutes=sum(i["minutes_added"] for i in impacts),
        summary=delays_service.affected_summary(affected),
        record=schema_info.record("flight_delay", "delay_id", delay_id),
    )


@bp.route("/<int:delay_id>/edit", methods=["GET", "POST"])
def edit(delay_id):
    notice = delays_service.get_delay(delay_id)
    if not notice:
        flash("Delay notice not found", "error")
        return redirect(url_for("delays.list_view"))
    if request.method == "POST":
        values, errors = editable_from_form(request.form)
        for e in errors:
            flash(e, "error")
        if not errors:
            with db_action("Delay notice updated"):
                delays_service.update_notice(delay_id, values)
            return redirect(url_for("delays.detail", delay_id=delay_id))
    return render_template("delays/edit.html", notice=notice)


@bp.route("/<int:delay_id>/resolve", methods=["POST"])
def resolve(delay_id):
    with db_action("Delay marked resolved"):
        delays_service.resolve(delay_id)
    return redirect(url_for("delays.detail", delay_id=delay_id))


@bp.route("/<int:delay_id>/rebook", methods=["POST"])
def rebook_all(delay_id):
    """Rebooks every passenger whose connection this notice broke."""
    notice = delays_service.get_delay(delay_id)
    if not notice:
        flash("Delay notice not found", "error")
        return redirect(url_for("delays.list_view"))
    affected = {notice["flight_id"]} | {i["flight_id"] for i in delays_service.impacts(delay_id)}
    rebooked, failures = operations.rebook_stranded(affected)
    if rebooked:
        flash(f"Rebooked {rebooked} {'passenger' if rebooked == 1 else 'passengers'} onto later flights", "success")
    for pnr, reason in failures:
        flash(f"{pnr}: {reason}", "error")
    if not rebooked and not failures:
        flash("No broken connections left to rebook", "success")
    return redirect(url_for("delays.detail", delay_id=delay_id))


@bp.route("/reset", methods=["GET", "POST"])
def reset():
    if request.method == "POST":
        with db_action("All delays cleared; every flight is back on schedule"):
            delays_service.reset_all()
        return redirect(url_for("delays.list_view"))
    return render_template("delays/reset.html", count=len(delays_service.list_delays()))
