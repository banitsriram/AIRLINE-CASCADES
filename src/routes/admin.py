from flask import Blueprint, render_template, request, redirect, url_for, flash, abort

from src.routes.helpers import db_action
from src.services import admin as admin_service

bp = Blueprint("admin", __name__)


def _require_entity(entity):
    if entity not in admin_service.ENTITIES:
        abort(404)
    return admin_service.ENTITIES[entity]


def _fk_options(flds):
    return {f["name"]: admin_service.fk_options(f["ref"]) for f in flds if f["type"] == "fk"}


@bp.route("/")
def index():
    return render_template("admin/index.html", entities=admin_service.ENTITIES)


def _name(cfg):
    item = cfg["item"]
    return item[0].upper() + item[1:]


@bp.route("/<entity>/")
def list_view(entity):
    cfg = _require_entity(entity)
    flds = admin_service.fields(entity)
    return render_template(
        "admin/list.html", entity=entity, cfg=cfg, fields=flds, rows=admin_service.list_rows(entity, flds)
    )


@bp.route("/<entity>/new", methods=["GET", "POST"])
def new(entity):
    cfg = _require_entity(entity)
    flds = admin_service.fields(entity)
    if request.method == "POST":
        with db_action(f"{_name(cfg)} created"):
            admin_service.create_row(entity, request.form, flds)
        return redirect(url_for("admin.list_view", entity=entity))
    return render_template(
        "admin/form.html", entity=entity, cfg=cfg, fields=flds, row=None, fk_options=_fk_options(flds)
    )


@bp.route("/<entity>/<int:row_id>/edit", methods=["GET", "POST"])
def edit(entity, row_id):
    cfg = _require_entity(entity)
    flds = admin_service.fields(entity)
    row = admin_service.get_row(entity, row_id, flds)
    if not row:
        flash("Not found", "error")
        return redirect(url_for("admin.list_view", entity=entity))
    if request.method == "POST":
        with db_action(f"{_name(cfg)} updated"):
            admin_service.update_row(entity, row_id, request.form, flds)
        return redirect(url_for("admin.list_view", entity=entity))
    return render_template(
        "admin/form.html", entity=entity, cfg=cfg, fields=flds, row=row, fk_options=_fk_options(flds)
    )


@bp.route("/<entity>/<int:row_id>/delete", methods=["POST"])
def delete(entity, row_id):
    _require_entity(entity)
    with db_action(f"{_name(admin_service.ENTITIES[entity])} deleted"):
        admin_service.delete_row(entity, row_id)
    return redirect(url_for("admin.list_view", entity=entity))
