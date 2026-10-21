"""CSRF protection for the HTML forms: a per-session token that every POST
form carries as a hidden field and every non-API POST must echo back. The
JSON API is exempt because it only accepts application/json, which a
cross-site form can't send."""

import hmac
import secrets

from flask import abort, current_app, request, session


def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_urlsafe(32)
    return session["_csrf"]


def init_app(app):
    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def check_csrf():
        if request.method != "POST" or request.blueprint == "api":
            return
        if not current_app.config.get("CSRF_ENABLED", True):
            return
        sent = request.form.get("csrf_token", "")
        expected = session.get("_csrf", "")
        if not expected or not hmac.compare_digest(sent, expected):
            abort(400, "The form expired or came from another site. Reload the page and try again.")
