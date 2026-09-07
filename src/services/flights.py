from src.db import query, execute

LIST_SELECT = """
    SELECT f.flight_id, f.flight_number, f.status, f.delay_minutes,
           f.sched_departure, f.sched_arrival, f.actual_departure, f.actual_arrival,
           o.iata_code AS origin, d.iata_code AS dest, ac.registration
    FROM flight f
    JOIN route r ON r.route_id = f.route_id
    JOIN airport o ON o.airport_id = r.origin_airport_id
    JOIN airport d ON d.airport_id = r.dest_airport_id
    JOIN aircraft ac ON ac.aircraft_id = f.aircraft_id
"""


def _dt(value):
    """datetime-local inputs submit 'YYYY-MM-DDTHH:MM'; MySQL wants a space."""
    if not value:
        return None
    return value.replace("T", " ")


def list_flights(status=None, date=None):
    sql = LIST_SELECT + " WHERE 1=1"
    params = []
    if status:
        sql += " AND f.status = %s"
        params.append(status)
    if date:
        sql += " AND DATE(f.sched_departure) = %s"
        params.append(date)
    sql += " ORDER BY f.sched_departure DESC"
    return query(sql, params)


def get_flight(flight_id):
    rows = query(
        LIST_SELECT.replace(
            "SELECT f.flight_id,", "SELECT f.*,"
        ) + " WHERE f.flight_id = %s",
        (flight_id,),
    )
    return rows[0] if rows else None


def crew_for_flight(flight_id):
    return query(
        """SELECT ca.crew_id, c.name, ca.role, ca.assigned_at
           FROM crew_assignment ca
           JOIN crew c ON c.crew_id = ca.crew_id
           WHERE ca.flight_id = %s AND ca.unassigned_at IS NULL""",
        (flight_id,),
    )


def delays_for_flight(flight_id):
    return query(
        """SELECT fd.delay_id, dr.category, dr.description, fd.minutes, fd.recorded_at
           FROM flight_delay fd
           JOIN delay_reason dr ON dr.reason_id = fd.reason_id
           WHERE fd.flight_id = %s
           ORDER BY fd.recorded_at""",
        (flight_id,),
    )


def create_flight(data):
    return execute(
        """INSERT INTO flight
           (flight_number, route_id, aircraft_id, sched_departure, sched_arrival,
            boarding_start, gate_close, status)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (
            data["flight_number"],
            data["route_id"],
            data["aircraft_id"],
            _dt(data["sched_departure"]),
            _dt(data["sched_arrival"]),
            _dt(data.get("boarding_start")),
            _dt(data.get("gate_close")),
            data.get("status") or "SCHEDULED",
        ),
    )


def update_flight(flight_id, data):
    execute(
        """UPDATE flight SET
             flight_number=%s, route_id=%s, aircraft_id=%s,
             sched_departure=%s, sched_arrival=%s,
             boarding_start=%s, gate_close=%s,
             actual_departure=%s, actual_arrival=%s, status=%s
           WHERE flight_id=%s""",
        (
            data["flight_number"],
            data["route_id"],
            data["aircraft_id"],
            _dt(data["sched_departure"]),
            _dt(data["sched_arrival"]),
            _dt(data.get("boarding_start")),
            _dt(data.get("gate_close")),
            _dt(data.get("actual_departure")),
            _dt(data.get("actual_arrival")),
            data.get("status") or "SCHEDULED",
            flight_id,
        ),
    )


def delete_flight(flight_id):
    execute("DELETE FROM flight WHERE flight_id=%s", (flight_id,))


def assign_crew(flight_id, crew_id, role):
    execute(
        "INSERT INTO crew_assignment (flight_id, crew_id, role) VALUES (%s, %s, %s)",
        (flight_id, crew_id, role),
    )


def unassign_crew(flight_id, crew_id):
    execute(
        "UPDATE crew_assignment SET unassigned_at = NOW() WHERE flight_id=%s AND crew_id=%s",
        (flight_id, crew_id),
    )
