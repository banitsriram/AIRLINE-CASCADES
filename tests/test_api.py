"""The JSON API at /api/v1."""
from src.db import query


def _scheduled_flight(days_ahead=2):
    return query(
        """SELECT flight_id FROM flight WHERE status = 'SCHEDULED' AND delay_minutes = 0
           AND DATE(sched_departure) = CURDATE() + INTERVAL %s DAY ORDER BY sched_departure LIMIT 1""",
        (days_ahead,),
    )[0]["flight_id"]


def test_flight_list_filters_by_date(client):
    day = query("SELECT DATE(MIN(sched_departure)) AS d FROM flight")[0]["d"]
    body = client.get(f"/api/v1/flights?date={day.isoformat()}").get_json()
    assert body["count"] == len(body["flights"]) > 0
    assert all(f["std"].startswith(day.isoformat()) for f in body["flights"])


def test_flight_detail_has_crew(client):
    flight_id = _scheduled_flight()
    body = client.get(f"/api/v1/flights/{flight_id}").get_json()
    assert body["flight_id"] == flight_id
    assert body["crew"]


def test_filing_a_delay_runs_the_cascade(client):
    flight_id = _scheduled_flight()
    r = client.post(f"/api/v1/flights/{flight_id}/delays",
                    json={"code": "41", "minutes": 150, "reported_by": "api test", "meal_voucher": True})
    assert r.status_code == 201
    body = r.get_json()
    assert body["notice"]["flight_id"] == flight_id
    assert body["notice"]["minutes"] == 150
    assert body["knock_on_flights"] == len(body["impacts"]) > 0
    assert client.get(f"/api/v1/flights/{flight_id}").get_json()["delay_minutes"] == 150


def test_invalid_notice_is_rejected_with_reasons(client):
    r = client.post(f"/api/v1/flights/{_scheduled_flight()}/delays", json={"minutes": 10})
    assert r.status_code == 422
    assert "Reported by is required" in r.get_json()["details"]


def test_airport_board_by_iata(client):
    body = client.get("/api/v1/airports/del/board").get_json()
    assert body["airport"]["iata_code"] == "DEL"
    assert isinstance(body["departures"], list)


def test_unknown_things_are_json_404s(client):
    for url in ("/api/v1/flights/999999", "/api/v1/delays/999999", "/api/v1/airports/zzz/board", "/api/v1/nope"):
        r = client.get(url)
        assert r.status_code == 404 and "error" in r.get_json(), url


def test_clock_endpoint(client):
    r = client.post("/api/v1/clock", json={"until": "2000-01-01T00:00"})
    assert r.status_code == 200 and r.get_json()["departed"] == 0
    assert client.post("/api/v1/clock", json={"until": "soon"}).status_code == 400
