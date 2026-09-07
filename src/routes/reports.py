from flask import Blueprint, render_template

from src.services import reports as reports_service

bp = Blueprint("reports", __name__)


@bp.route("/")
def index():
    return render_template("reports/index.html")


@bp.route("/ontime")
def ontime():
    return render_template("reports/ontime.html", rows=reports_service.ontime_performance())


@bp.route("/delay-causes")
def delay_causes():
    return render_template("reports/delay_causes.html", rows=reports_service.top_delay_causes())


@bp.route("/load-factor")
def load_factor():
    return render_template("reports/load_factor.html", rows=reports_service.load_factor())


@bp.route("/duty-status")
def duty_status():
    return render_template("reports/duty_status.html", rows=reports_service.duty_status())


@bp.route("/utilisation")
def utilisation():
    return render_template("reports/utilisation.html", rows=reports_service.aircraft_utilisation())
