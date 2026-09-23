from flask import Blueprint, render_template, abort, request

from src.services import schema_info

bp = Blueprint("schema", __name__)


@bp.route("/")
def index():
    return render_template("schema/index.html", tables=schema_info.tables(), views=schema_info.views())


@bp.route("/<table_name>")
def table_detail(table_name):
    names = {t["table_name"] for t in schema_info.tables() + schema_info.views()}
    if table_name not in names:
        abort(404)
    return render_template(
        "schema/table.html",
        table_name=table_name,
        columns=schema_info.columns(table_name),
        foreign_keys=schema_info.foreign_keys(table_name),
    )


@bp.route("/<table_name>/rows")
def rows(table_name):
    names = {t["table_name"] for t in schema_info.tables() + schema_info.views()}
    if table_name not in names:
        abort(404)
    page = max(1, request.args.get("page", 1, type=int))
    cols, data, total = schema_info.rows_page(table_name, page)
    return render_template(
        "schema/rows.html", table_name=table_name, cols=cols, rows=data,
        total=total, page=page, pages=max(1, -(-total // 50)),
    )
