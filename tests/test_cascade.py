"""The organisation-wide cascade engine, simulate_delay(), end to end."""
import mysql.connector
import pytest

from src.db import query, call_proc, execute
from src.services import delays

pytestmark = pytest.mark.usefixtures("fresh_db")


def _violations():
    call_proc("compute_cascade_candidates", (None, None))
    return query(
        """SELECT c.link, COUNT(*) AS n FROM cascade_candidate c JOIN flight f USING (flight_id)
           WHERE c.required_delay > f.delay_minutes GROUP BY c.link"""
    )


def _notice(**overrides):
    notice = {f: None for f in delays.NOTICE_FIELDS}
    notice.update(phase="AT_GATE", ops_status="DELAYED", reported_by="test", pax_deboarded=False,
                  meal_voucher=False, compensation_eligible=False, rebooking_offered=False)
    notice.update(overrides)
    return notice


def _code(iata):
    return query("SELECT code_id FROM delay_code WHERE iata_code = %s", (iata,))[0]["code_id"]


def test_seeded_schedule_is_consistent_at_zero_delay():
    """With no delays filed, every cascade rule is already satisfied and no flag
    view has rows, so flights only ever move because of a filed delay."""
    call_proc("reset_all_delays")
    assert not _violations()
    for view in ("v_missed_connections", "v_duty_breaches", "v_curfew_risk"):
        assert query(f"SELECT COUNT(*) AS n FROM {view}")[0]["n"] == 0, view


def test_delay_reaches_aircraft_crew_and_passengers():
    """A hub-bound leg whose crew continue on another aircraft and which carries
    connecting passengers: the delay must reach the same aircraft's next leg, a
    different aircraft through its crew, and break at least one connection."""
    flight = query(
        """SELECT f.flight_id, f.aircraft_id
           FROM flight f
           WHERE f.status = 'SCHEDULED' AND DATE(f.sched_departure) = CURDATE() + INTERVAL 1 DAY
             AND EXISTS (SELECT 1 FROM crew_assignment ca
                         JOIN crew_assignment ca2 ON ca2.crew_id = ca.crew_id
                         JOIN flight f2 ON f2.flight_id = ca2.flight_id
                         WHERE ca.flight_id = f.flight_id AND f2.aircraft_id <> f.aircraft_id
                           AND f2.sched_departure > f.sched_departure
                           AND DATE(f2.sched_departure) = DATE(f.sched_departure))
             AND EXISTS (SELECT 1 FROM ticket t JOIN ticket t2 ON t2.booking_id = t.booking_id
                         AND t2.flight_id <> t.flight_id WHERE t.flight_id = f.flight_id)
           ORDER BY f.sched_departure LIMIT 1"""
    )[0]
    delay_id = delays.file_delay(flight["flight_id"], _notice(minutes=180, code_id=_code("41")))

    impacts = query(
        """SELECT di.link, di.flight_id, f.aircraft_id
           FROM delay_impact di JOIN flight f USING (flight_id) WHERE di.delay_id = %s""",
        (delay_id,),
    )
    assert any(i["link"] == "AIRCRAFT" and i["aircraft_id"] == flight["aircraft_id"] for i in impacts)
    assert any(i["link"] == "CREW" and i["aircraft_id"] != flight["aircraft_id"] for i in impacts)
    affected = [flight["flight_id"]] + [i["flight_id"] for i in impacts]
    assert delays.affected_summary(affected)["missed"]


def test_knock_on_counts_flights_not_impact_rows():
    """A flight moved in several passes has several impact rows but is one
    delayed flight, on the delay log and the impact page alike."""
    delay = query("""SELECT delay_id, flight_id FROM flight_delay
                     WHERE reported_by = 'test' ORDER BY delay_id DESC LIMIT 1""")[0]
    rows = delays.impacts(delay["delay_id"])
    distinct = {r["flight_id"] for r in rows} - {delay["flight_id"]}
    listed = next(d for d in delays.list_delays() if d["delay_id"] == delay["delay_id"])
    assert listed["knock_on_flights"] == len(distinct)
    assert len(rows) > len(distinct), "this delay should move some flight more than once"


def test_every_delay_is_accounted_for():
    """Each flight's delay is exactly what was filed on it plus its knock-on."""
    assert not query(
        """SELECT f.flight_id FROM flight f
           LEFT JOIN (SELECT flight_id, SUM(minutes) AS m FROM flight_delay GROUP BY flight_id) d USING (flight_id)
           LEFT JOIN (SELECT flight_id, SUM(minutes_added) AS m FROM delay_impact GROUP BY flight_id) k USING (flight_id)
           WHERE f.delay_minutes <> COALESCE(d.m, 0) + COALESCE(k.m, 0)"""
    )


def test_cascade_settles_with_no_rule_violated():
    assert not _violations()


def test_cancellation_pushes_nothing_downstream():
    flight_id = query(
        """SELECT flight_id FROM flight WHERE status = 'SCHEDULED' AND delay_minutes = 0
           AND DATE(sched_departure) = CURDATE() + INTERVAL 4 DAY ORDER BY sched_departure LIMIT 1"""
    )[0]["flight_id"]
    delay_id = delays.file_delay(flight_id, _notice(minutes=0, code_id=_code("41"), ops_status="CANCELLED"))
    assert query("SELECT status FROM flight WHERE flight_id = %s", (flight_id,))[0]["status"] == "CANCELLED"
    assert not delays.impacts(delay_id)


def test_cannot_delay_a_landed_flight():
    flight_id = query("SELECT flight_id FROM flight ORDER BY sched_departure LIMIT 1")[0]["flight_id"]
    execute("UPDATE flight SET status = 'ARRIVED', actual_departure = sched_departure, "
            "actual_arrival = sched_arrival WHERE flight_id = %s", (flight_id,))
    with pytest.raises(mysql.connector.Error, match="arrived"):
        delays.file_delay(flight_id, _notice(minutes=30, code_id=_code("41")))


def test_reset_puts_the_network_back_on_schedule():
    call_proc("reset_all_delays")
    assert query("SELECT COUNT(*) AS n FROM flight WHERE delay_minutes <> 0")[0]["n"] == 0
    assert query("SELECT COUNT(*) AS n FROM delay_impact")[0]["n"] == 0
    assert query("SELECT COUNT(*) AS n FROM flight WHERE status = 'CANCELLED'")[0]["n"] == 0
