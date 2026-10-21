"""Every page renders on the seeded database, and the main write flows work
through the HTML forms."""
import re

import pytest

from src.db import query


def _ids():
    one = lambda sql: query(sql)[0]["id"]  # noqa: E731
    return {
        "flight_id": one("SELECT flight_id AS id FROM flight WHERE status = 'SCHEDULED' ORDER BY sched_departure LIMIT 1"),
        "delay_id": one("SELECT MIN(delay_id) AS id FROM flight_delay"),
        "airport_id": one("SELECT MIN(airport_id) AS id FROM airport"),
        "crew_id": one("SELECT MIN(crew_id) AS id FROM crew"),
        "passenger_id": one("SELECT MIN(passenger_id) AS id FROM passenger"),
        "booking_id": one("SELECT MIN(booking_id) AS id FROM booking"),
        "entity": "airport",
        "row_id": one("SELECT MIN(airport_id) AS id FROM airport"),
        "table": "flight",
    }


def test_every_get_page_renders(client):
    ids = _ids()
    from app import app
    checked = 0
    for rule in app.url_map.iter_rules():
        if "GET" not in rule.methods or rule.endpoint == "static" or rule.rule.startswith("/api/"):
            continue
        if any(arg not in ids for arg in rule.arguments):
            continue
        url = rule.rule
        for arg in rule.arguments:
            url = re.sub(rf"<(?:\w+:)?{arg}>", str(ids[arg]), url)
        r = client.get(url)
        assert r.status_code == 200, (url, r.status_code)
        checked += 1
    assert checked > 30


def test_filing_a_delay_through_the_form(client):
    flight_id = _ids()["flight_id"]
    code_id = query("SELECT code_id FROM delay_code WHERE iata_code = '81'")[0]["code_id"]
    r = client.post(f"/flights/{flight_id}/delay", data={
        "code_id": code_id, "minutes": "40", "phase": "AT_GATE", "ops_status": "DELAYED",
        "reported_by": "form test", "meal_voucher": "on",
    })
    assert r.status_code == 302 and "/delays/" in r.headers["Location"]
    page = client.get(r.headers["Location"]).get_data(as_text=True)
    assert "Knock-on effects" in page


def test_booking_flow(client):
    passenger_id = _ids()["passenger_id"]
    flight_id = query(
        """SELECT flight_id FROM flight WHERE status = 'SCHEDULED' ORDER BY sched_departure DESC LIMIT 1"""
    )[0]["flight_id"]
    r = client.post("/bookings/new", data={"passenger_id": passenger_id, "flight_id": flight_id,
                                          "seat_no": "29F", "ticket_class": "ECONOMY", "fare": "4999"})
    assert r.status_code == 302
    booking_page = client.get(r.headers["Location"]).get_data(as_text=True)
    assert "29F" in booking_page

    # The same seat can't be sold twice
    r = client.post("/bookings/new", data={"passenger_id": passenger_id, "flight_id": flight_id,
                                          "seat_no": "29F", "ticket_class": "ECONOMY", "fare": "4999"})
    assert "Seat already booked" in r.get_data(as_text=True)


@pytest.mark.parametrize("url", ["/flights/999999", "/delays/999999", "/bookings/999999"])
def test_missing_records_redirect(client, url):
    assert client.get(url).status_code == 302
