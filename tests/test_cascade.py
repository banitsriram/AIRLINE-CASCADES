"""Run against a freshly seeded DB:
    bash scripts/setup_db.sh && python tests/test_cascade.py
Checks the organisation-wide cascade engine (simulate_delay) end to end."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db import query, call_proc
from src.services import delays

call_proc("reset_all_delays")

# 1. With no delays filed, the seeded schedule satisfies every cascade rule and
#    raises no flags -- so flights only ever move because of a filed delay.
call_proc("compute_cascade_candidates")
violations = query(
    """SELECT c.link, COUNT(*) AS n FROM cascade_candidate c JOIN flight f USING (flight_id)
       WHERE c.required_delay > f.delay_minutes GROUP BY c.link"""
)
assert not violations, f"schedule breaks cascade rules at zero delay: {violations}"
for view in ("v_missed_connections", "v_duty_breaches", "v_curfew_risk"):
    assert query(f"SELECT COUNT(*) AS n FROM {view}")[0]["n"] == 0, f"{view} not empty at zero delay"

# 2. Delay a hub-bound leg whose crew continue on another aircraft and which
#    carries connecting passengers: the delay must reach the same aircraft's next
#    leg, a different aircraft via crew, and break at least one connection.
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
code_id = query("SELECT code_id FROM delay_code WHERE iata_code = '41'")[0]["code_id"]
notice = {f: None for f in delays.NOTICE_FIELDS}
notice.update(minutes=180, code_id=code_id, phase="AT_GATE", ops_status="DELAYED", reported_by="test",
              pax_deboarded=False, meal_voucher=True, compensation_eligible=True, rebooking_offered=False)
delay_id = delays.file_delay(flight["flight_id"], notice)

impacts = query(
    """SELECT di.link, di.flight_id, di.minutes_added, f.aircraft_id
       FROM delay_impact di JOIN flight f USING (flight_id) WHERE di.delay_id = %s""",
    (delay_id,),
)
assert any(i["link"] == "AIRCRAFT" and i["aircraft_id"] == flight["aircraft_id"] for i in impacts), impacts
assert any(i["link"] == "CREW" and i["aircraft_id"] != flight["aircraft_id"] for i in impacts), impacts
affected = [flight["flight_id"]] + [i["flight_id"] for i in impacts]
assert delays.affected_summary(affected)["missed"], "expected at least one missed connection"

# 3. Every flight's delay is exactly what was filed on it plus its knock-on.
mismatched = query(
    """SELECT f.flight_id FROM flight f
       LEFT JOIN (SELECT flight_id, SUM(minutes) AS m FROM flight_delay GROUP BY flight_id) d USING (flight_id)
       LEFT JOIN (SELECT flight_id, SUM(minutes_added) AS m FROM delay_impact GROUP BY flight_id) k USING (flight_id)
       WHERE f.delay_minutes <> COALESCE(d.m, 0) + COALESCE(k.m, 0)"""
)
assert not mismatched, mismatched

# 4. After the cascade settles, no rule is left violated.
call_proc("compute_cascade_candidates")
assert not query(
    """SELECT 1 FROM cascade_candidate c JOIN flight f USING (flight_id)
       WHERE c.required_delay > f.delay_minutes LIMIT 1"""
), "cascade stopped before every rule was satisfied"

# 5. Reset puts the whole network back on schedule.
call_proc("reset_all_delays")
assert query("SELECT COUNT(*) AS n FROM flight WHERE delay_minutes <> 0")[0]["n"] == 0
assert query("SELECT COUNT(*) AS n FROM delay_impact")[0]["n"] == 0

print(f"ok ({len(impacts)} knock-on flights)")
