"""Soft-unassigned crew are really treated as off the flight."""
import pytest

from src.db import query, execute
from src.services import flights

pytestmark = pytest.mark.usefixtures("fresh_db")


@pytest.fixture(scope="module")
def flight_and_crew():
    flight = query(
        "SELECT flight_id, DATE(sched_departure) d FROM flight WHERE actual_arrival IS NULL ORDER BY flight_id LIMIT 1"
    )[0]
    # Someone not on this flight with no duty that day, so any duty_log row
    # would have to come from this flight.
    crew = query(
        """SELECT c.crew_id, c.role FROM crew c
           WHERE c.terminated_at IS NULL
             AND NOT EXISTS (SELECT 1 FROM crew_assignment ca WHERE ca.crew_id = c.crew_id AND ca.flight_id = %s)
             AND NOT EXISTS (SELECT 1 FROM duty_log d WHERE d.crew_id = c.crew_id AND d.duty_date = %s)
           LIMIT 1""",
        (flight["flight_id"], flight["d"]),
    )[0]
    return flight, crew


def test_reassigning_reactivates_the_row(flight_and_crew):
    flight, crew = flight_and_crew
    f = flight["flight_id"]
    flights.assign_crew(f, crew["crew_id"], crew["role"])
    flights.unassign_crew(f, crew["crew_id"])
    flights.assign_crew(f, crew["crew_id"], crew["role"])
    row = query("SELECT unassigned_at FROM crew_assignment WHERE flight_id=%s AND crew_id=%s", (f, crew["crew_id"]))
    assert row[0]["unassigned_at"] is None
    flights.unassign_crew(f, crew["crew_id"])


def test_unassigned_crew_get_no_duty_hours(flight_and_crew):
    flight, crew = flight_and_crew
    execute("UPDATE flight SET actual_departure=sched_departure, actual_arrival=sched_arrival WHERE flight_id=%s",
            (flight["flight_id"],))
    assert not query("SELECT 1 FROM duty_log WHERE crew_id=%s AND duty_date=%s", (crew["crew_id"], flight["d"]))


def test_assigned_crew_do_get_duty_hours(flight_and_crew):
    flight, _ = flight_and_crew
    on_board = query("SELECT crew_id FROM crew_assignment WHERE flight_id=%s AND unassigned_at IS NULL",
                     (flight["flight_id"],))
    assert on_board
    for c in on_board:
        assert query("SELECT hours_flown FROM duty_log WHERE crew_id=%s AND duty_date=%s",
                     (c["crew_id"], flight["d"]))[0]["hours_flown"] > 0
