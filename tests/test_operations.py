"""The operations clock (advance_clock) and rebooking (rebook_ticket)."""
from datetime import datetime, timedelta

import mysql.connector
import pytest

from src.db import query
from src.services import operations

pytestmark = pytest.mark.usefixtures("fresh_db")


def _count(sql, params=()):
    return query(sql, params)[0]["n"]


def test_rebooking_restores_a_broken_connection():
    stranded = operations.stranded_tickets(
        [r["flight_id"] for r in query("SELECT flight_id FROM flight WHERE delay_minutes > 0")]
    )
    assert stranded, "the sample delays should break some connections"
    before = _count("SELECT COUNT(*) AS n FROM v_missed_connections")

    ticket = stranded[0]
    old = query("SELECT flight_id, seat_no FROM ticket WHERE ticket_id = %s", (ticket["ticket_id"],))[0]
    new_flight = operations.rebook_ticket(ticket["ticket_id"], ticket["reason"])

    moved = query("SELECT flight_id, seat_no FROM ticket WHERE ticket_id = %s", (ticket["ticket_id"],))[0]
    assert moved["flight_id"] == new_flight != old["flight_id"]
    assert query(
        "SELECT old_flight_id, new_flight_id, old_seat_no FROM rebooking WHERE ticket_id = %s",
        (ticket["ticket_id"],),
    ) == [{"old_flight_id": old["flight_id"], "new_flight_id": new_flight, "old_seat_no": old["seat_no"]}]
    assert _count("SELECT COUNT(*) AS n FROM v_missed_connections") < before


def test_rebooked_flight_is_on_the_same_route_and_makeable():
    row = query(
        """SELECT fo.route_id AS old_route, fn.route_id AS new_route, fn.etd, t.booking_id, fn.origin_airport_id
           FROM rebooking rb
           JOIN ticket t ON t.ticket_id = rb.ticket_id
           JOIN v_flight_times fo ON fo.flight_id = rb.old_flight_id
           JOIN v_flight_times fn ON fn.flight_id = rb.new_flight_id
           LIMIT 1"""
    )[0]
    assert row["old_route"] == row["new_route"]
    inbound = query(
        """SELECT fi.eta, ap.min_connect_min FROM ticket ti
           JOIN v_flight_times fi ON fi.flight_id = ti.flight_id
           JOIN airport ap ON ap.airport_id = fi.dest_airport_id
           WHERE ti.booking_id = %s AND fi.dest_airport_id = %s""",
        (row["booking_id"], row["origin_airport_id"]),
    )[0]
    assert row["etd"] >= inbound["eta"] + timedelta(minutes=inbound["min_connect_min"])


def test_rebooking_unknown_ticket_fails_cleanly():
    with pytest.raises(mysql.connector.Error, match="Ticket not found"):
        operations.rebook_ticket(10_000_000, "PASSENGER_REQUEST")


def test_clock_moves_flights_through_their_lifecycle():
    until = datetime.combine(datetime.now().date() + timedelta(days=1), datetime.min.time()) + timedelta(hours=12)
    duty_before = _count("SELECT COUNT(*) AS n FROM duty_log")
    moved = operations.advance_clock(until)

    assert moved["arrived"] > 0
    # Nothing left behind the clock, nothing ahead of it moved
    assert _count(
        """SELECT COUNT(*) AS n FROM v_flight_times
           WHERE status IN ('SCHEDULED', 'BOARDING') AND etd <= %s""", (until,)) == 0
    assert _count(
        """SELECT COUNT(*) AS n FROM v_flight_times
           WHERE status IN ('DEPARTED', 'ARRIVED') AND etd > %s""", (until,)) == 0
    # Actual times are the estimates, and arrivals booked crew duty
    assert _count(
        """SELECT COUNT(*) AS n FROM v_flight_times
           WHERE status = 'ARRIVED' AND (actual_departure <> etd OR actual_arrival <> eta)""") == 0
    assert _count("SELECT COUNT(*) AS n FROM duty_log") > duty_before


def test_clock_closes_notices_and_completes_journeys():
    assert _count(
        """SELECT COUNT(*) AS n FROM flight_delay fd JOIN flight f USING (flight_id)
           WHERE f.status IN ('DEPARTED', 'ARRIVED') AND fd.resolved_at IS NULL""") == 0
    assert _count("SELECT COUNT(*) AS n FROM booking WHERE status = 'COMPLETED'") > 0


def test_clock_never_runs_backwards():
    arrived = _count("SELECT COUNT(*) AS n FROM flight WHERE status = 'ARRIVED'")
    moved = operations.advance_clock(datetime(2000, 1, 1))
    assert moved["departed"] == moved["arrived"] == moved["boarding"] == 0
    assert _count("SELECT COUNT(*) AS n FROM flight WHERE status = 'ARRIVED'") == arrived
