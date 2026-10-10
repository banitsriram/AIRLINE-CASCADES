import os
from datetime import date, datetime, timedelta
from decimal import Decimal

from flask import Flask, jsonify, render_template, request
from flask.json.provider import DefaultJSONProvider
import mysql.connector

from src.config import Settings
from src.db import query
from src.services.lookups import enum_values
from src.routes import (
    admin,
    airports,
    api,
    bookings,
    cascade,
    crew,
    dashboard,
    delays,
    flights,
    passengers,
    reports,
    schema,
)


class JSONProvider(DefaultJSONProvider):
    """ISO 8601 datetimes, MySQL TIME values as HH:MM:SS, DECIMAL as numbers."""

    @staticmethod
    def default(o):
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        if isinstance(o, timedelta):
            seconds = int(o.total_seconds())
            return f"{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}"
        if isinstance(o, Decimal):
            return float(o)
        return DefaultJSONProvider.default(o)


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.json = JSONProvider(app)
    app.config.from_object(Settings)

    app.register_blueprint(dashboard.bp)
    app.register_blueprint(flights.bp, url_prefix="/flights")
    app.register_blueprint(cascade.bp, url_prefix="/cascade")
    app.register_blueprint(crew.bp, url_prefix="/crew")
    app.register_blueprint(passengers.bp, url_prefix="/passengers")
    app.register_blueprint(bookings.bp, url_prefix="/bookings")
    app.register_blueprint(reports.bp, url_prefix="/reports")
    app.register_blueprint(admin.bp, url_prefix="/admin")
    app.register_blueprint(schema.bp, url_prefix="/schema")
    app.register_blueprint(delays.bp, url_prefix="/delays")
    app.register_blueprint(airports.bp, url_prefix="/airports")
    app.register_blueprint(api.bp, url_prefix="/api/v1")

    app.jinja_env.globals["enum_values"] = enum_values

    @app.errorhandler(mysql.connector.Error)
    def database_error(err):
        """A table was changed by hand in a way this page depends on (a dropped or
        renamed column, a missing table...). Say exactly what MySQL reported."""
        return render_template("error.html", title="The database rejected this page",
                               message=err.msg, code=err.errno), 500

    @app.errorhandler(404)
    def not_found(err):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Not found"}), 404
        return render_template("error.html", title="Nothing here",
                               message="That page or record doesn't exist. It may have been deleted.", code=404), 404

    @app.context_processor
    def nav_counts():
        """Late-flight count shown in the nav on every page. If the flight table
        has been altered so this can't run, the nav just omits it (the page's own
        error, if any, is reported by database_error)."""
        try:
            return {"delayed_now": query(
                "SELECT COUNT(*) AS n FROM flight WHERE delay_minutes > 0 AND status IN ('SCHEDULED', 'BOARDING', 'DEPARTED')"
            )[0]["n"]}
        except mysql.connector.Error:
            return {"delayed_now": 0}

    @app.template_filter("human")
    def human(value):
        """Database enum values for display: FIRST_OFFICER -> First officer, ATC stays ATC."""
        if not value:
            return value
        text = str(value)
        return text if len(text) <= 3 else text.replace("_", " ").capitalize()

    @app.template_filter("when")
    def when(value):
        """Datetimes as 'Wed 23 Sep, 18:28'; dates as 'Wed 23 Sep 2026'; anything else unchanged."""
        if hasattr(value, "hour"):
            return value.strftime("%a %d %b, %H:%M")
        if hasattr(value, "strftime"):
            return value.strftime("%a %d %b %Y")
        return value

    @app.template_filter("hhmm")
    def hhmm(value):
        """Formats datetimes and MySQL TIME values (timedeltas) as HH:MM."""
        if value is None:
            return ""
        if hasattr(value, "strftime"):
            return value.strftime("%H:%M")
        minutes = int(value.total_seconds()) // 60
        return f"{minutes // 60:02d}:{minutes % 60:02d}"

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "1") == "1", port=int(os.environ.get("PORT", 5000)))
