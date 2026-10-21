"""CSRF protection on the HTML forms, and the API refusing non-JSON writes."""
import re

import pytest

from app import app as flask_app
from src.db import query


@pytest.fixture
def guarded_client(fresh_db):
    flask_app.config.update(TESTING=True, CSRF_ENABLED=True)
    yield flask_app.test_client()
    flask_app.config["CSRF_ENABLED"] = False


def _flight_id():
    return query("SELECT flight_id FROM flight WHERE status = 'SCHEDULED' ORDER BY sched_departure DESC LIMIT 1")[0]["flight_id"]


def test_form_post_without_token_is_refused(guarded_client):
    r = guarded_client.post("/delays/reset")
    assert r.status_code == 400
    assert query("SELECT COUNT(*) AS n FROM flight_delay")[0]["n"] > 0


def test_form_post_with_the_pages_token_goes_through(guarded_client):
    page = guarded_client.get("/delays/reset").get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
    r = guarded_client.post("/delays/reset", data={"csrf_token": token})
    assert r.status_code == 302
    assert query("SELECT COUNT(*) AS n FROM flight_delay")[0]["n"] == 0


def test_every_post_form_carries_a_token(guarded_client):
    for url in ("/", f"/flights/{_flight_id()}", "/delays/reset", "/admin/airport/new", "/bookings/new"):
        html = guarded_client.get(url).get_data(as_text=True)
        forms = re.findall(r'<form\b[^>]*method="post"[^>]*>(.*?)</form>', html, flags=re.S)
        assert forms, url
        assert all('name="csrf_token"' in f for f in forms), url


def test_api_writes_must_be_json(guarded_client):
    r = guarded_client.post("/api/v1/clock", data={"until": "2030-01-01T00:00"})
    assert r.status_code == 415
    r = guarded_client.post(f"/api/v1/flights/{_flight_id()}/delays", data={"minutes": "30"})
    assert r.status_code == 415
