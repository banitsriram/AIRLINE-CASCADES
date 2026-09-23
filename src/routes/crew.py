from flask import Blueprint, render_template, request, redirect, url_for, flash

from src.routes.helpers import db_action
from src.services import crew as crew_service
from src.services import lookups
from src.services import schema_info

bp = Blueprint("crew", __name__)


@bp.route("/")
def list_view():
    role = request.args.get("role") or None
    return render_template("crew/list.html", crew=crew_service.list_crew(role=role), role=role)


@bp.route("/duty")
def duty():
    return render_template("crew/duty.html", duty=crew_service.duty_status())


@bp.route("/replacement/<int:flight_id>")
def replacement(flight_id):
    return render_template(
        "crew/replacement.html",
        flight_id=flight_id,
        candidates=crew_service.replacement_crew(flight_id),
    )


@bp.route("/<int:crew_id>")
def detail(crew_id):
    member = crew_service.get_crew(crew_id)
    if not member:
        flash("Crew member not found", "error")
        return redirect(url_for("crew.list_view"))
    return render_template(
        "crew/detail.html",
        crew=member,
        certs=crew_service.certifications(crew_id),
        aircraft_types=lookups.aircraft_types(),
        record=schema_info.record("crew", "crew_id", crew_id),
    )


@bp.route("/new", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        with db_action("Crew member created"):
            crew_service.create_crew(request.form)
        return redirect(url_for("crew.list_view"))
    return render_template("crew/form.html", crew=None, airports=lookups.airports())


@bp.route("/<int:crew_id>/edit", methods=["GET", "POST"])
def edit(crew_id):
    member = crew_service.get_crew(crew_id)
    if not member:
        flash("Crew member not found", "error")
        return redirect(url_for("crew.list_view"))
    if request.method == "POST":
        with db_action("Crew member updated"):
            crew_service.update_crew(crew_id, request.form)
        return redirect(url_for("crew.detail", crew_id=crew_id))
    return render_template("crew/form.html", crew=member, airports=lookups.airports())


@bp.route("/<int:crew_id>/delete", methods=["POST"])
def delete(crew_id):
    with db_action("Crew member deleted"):
        crew_service.delete_crew(crew_id)
    return redirect(url_for("crew.list_view"))


@bp.route("/<int:crew_id>/certify", methods=["POST"])
def certify(crew_id):
    with db_action("Certification added"):
        crew_service.add_certification(
            crew_id,
            request.form["type_id"],
            request.form["certified_date"],
            request.form["expiry_date"],
        )
    return redirect(url_for("crew.detail", crew_id=crew_id))


@bp.route("/<int:crew_id>/certify/<int:type_id>/delete", methods=["POST"])
def decertify(crew_id, type_id):
    with db_action("Certification removed"):
        crew_service.remove_certification(crew_id, type_id)
    return redirect(url_for("crew.detail", crew_id=crew_id))
