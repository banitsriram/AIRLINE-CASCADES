from flask import Blueprint, render_template, abort

from src.services import schema_info

bp = Blueprint("schema", __name__)


@bp.route("/")
def index():
    return render_template("schema/index.html", tables=schema_info.tables())


@bp.route("/<table_name>")
def table_detail(table_name):
    names = {t["table_name"] for t in schema_info.tables()}
    if table_name not in names:
        abort(404)
    return render_template(
        "schema/table.html",
        table_name=table_name,
        columns=schema_info.columns(table_name),
        foreign_keys=schema_info.foreign_keys(table_name),
    )
