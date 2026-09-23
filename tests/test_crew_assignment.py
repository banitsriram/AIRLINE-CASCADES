"""Run against a freshly seeded DB:
    bash scripts/setup_db.sh && python tests/test_crew_assignment.py
Checks that soft-unassigned crew are really treated as off the flight."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db import query, execute
from src.services import flights

flight = query(
    "SELECT flight_id, DATE(sched_departure) d FROM flight WHERE actual_arrival IS NULL ORDER BY flight_id LIMIT 1"
)[0]
f, day = flight["flight_id"], flight["d"]
# A crew member not on this flight with no duty that day, so any duty_log row would come from this flight.
crew = query(
    """SELECT c.crew_id, c.role FROM crew c
       WHERE c.terminated_at IS NULL
         AND NOT EXISTS (SELECT 1 FROM crew_assignment ca WHERE ca.crew_id = c.crew_id AND ca.flight_id = %s)
         AND NOT EXISTS (SELECT 1 FROM duty_log d WHERE d.crew_id = c.crew_id AND d.duty_date = %s)
       LIMIT 1""",
    (f, day),
)[0]

# Re-assigning after unassign must reactivate the row, not hit the composite PK.
flights.assign_crew(f, crew["crew_id"], crew["role"])
flights.unassign_crew(f, crew["crew_id"])
flights.assign_crew(f, crew["crew_id"], crew["role"])
row = query("SELECT unassigned_at FROM crew_assignment WHERE flight_id=%s AND crew_id=%s", (f, crew["crew_id"]))
assert row[0]["unassigned_at"] is None
flights.unassign_crew(f, crew["crew_id"])

# Unassigned crew must not accrue duty hours when the flight lands (trg_update_duty).
execute("UPDATE flight SET actual_departure=sched_departure, actual_arrival=sched_arrival WHERE flight_id=%s", (f,))
assert not query("SELECT 1 FROM duty_log WHERE crew_id=%s AND duty_date=%s", (crew["crew_id"], day)), "unassigned crew got duty hours"

print("ok")
