from flask import Flask

from src.config import Settings
from src.routes import (
    admin,
    bookings,
    cascade,
    crew,
    dashboard,
    flights,
    passengers,
    reports,
    schema,
)


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
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

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
