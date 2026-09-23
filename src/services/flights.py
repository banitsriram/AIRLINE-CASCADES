from src.db import query, execute

# v_flight_times (06_views.sql) derives ETD/ETA/display status from delay_minutes.
LIST_SELECT = """
    SELECT ft.*, ft.std AS sched_departure, ft.sta AS sched_arrival
    FROM v_flight_times ft
"""


def _dt(value):
    """datetime-local inputs submit 'YYYY-MM-DDTHH:MM'; MySQL wants a space."""
    if not value:
        return None
    return value.replace("T", " ")


def list_flights(status=None, date=None, q=None):
    sql = LIST_SELECT + " WHERE 1=1"
    params = []
    if status == "DELAYED":
        sql += " AND ft.display_status = 'DELAYED'"
    elif status:
        sql += " AND ft.status = %s"
        params.append(status)
    if date:
        sql += " AND DATE(ft.std) = %s"
        params.append(date)
    if q:
        sql += " AND (ft.flight_number LIKE %s OR ft.origin = %s OR ft.dest = %s OR ft.registration LIKE %s)"
        params += [f"%{q}%", q.upper(), q.upper(), f"%{q}%"]
    sql += " ORDER BY ft.std"
    return query(sql, params)


def get_flight(flight_id):
    rows = query(
        """SELECT ft.*, ft.std AS sched_departure, ft.sta AS sched_arrival, f.gate_close,
                  og.gate_code AS gate_label, o.city AS origin_city, d.city AS dest_city
           FROM v_flight_times ft
           JOIN flight f ON f.flight_id = ft.flight_id
           JOIN airport o ON o.airport_id = ft.origin_airport_id
           JOIN airport d ON d.airport_id = ft.dest_airport_id
           LEFT JOIN gate og ON og.gate_id = ft.gate_id
           WHERE ft.flight_id = %s""",
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
    """Delay notices filed directly on this flight."""
    return query(
        """SELECT fd.delay_id, dr.category, dc.iata_code, dc.description, fd.sub_reason,
                  fd.minutes, fd.ops_status, fd.reported_by, fd.recorded_at, fd.resolved_at
           FROM flight_delay fd
           JOIN delay_code dc ON dc.code_id = fd.code_id
           JOIN delay_reason dr ON dr.reason_id = dc.reason_id
           WHERE fd.flight_id = %s
           ORDER BY fd.recorded_at""",
        (flight_id,),
    )


def knock_on_for_flight(flight_id):
    """Delay this flight received from other flights' notices via the cascade."""
    return query(
        """SELECT di.delay_id, di.link, di.minutes_added, di.old_etd, di.new_etd,
                  cf.flight_id AS cause_flight_id, cf.flight_number AS cause_flight,
                  src.flight_number AS source_flight
           FROM delay_impact di
           JOIN flight_delay fd ON fd.delay_id = di.delay_id
           JOIN flight src ON src.flight_id = fd.flight_id
           LEFT JOIN flight cf ON cf.flight_id = di.cause_flight_id
           WHERE di.flight_id = %s
           ORDER BY di.impact_id""",
        (flight_id,),
    )


def gate_matches_route(gate_id, route_id):
    if not gate_id:
        return True
    return bool(query(
        """SELECT 1 FROM gate g JOIN route r ON r.origin_airport_id = g.airport_id
           WHERE g.gate_id = %s AND r.route_id = %s""",
        (gate_id, route_id),
    ))


def create_flight(data):
    return execute(
        """INSERT INTO flight
           (flight_number, route_id, aircraft_id, sched_departure, sched_arrival,
            boarding_start, gate_close, status, gate_id, remarks)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (
            data["flight_number"],
            data["route_id"],
            data["aircraft_id"],
            _dt(data["sched_departure"]),
            _dt(data["sched_arrival"]),
            _dt(data.get("boarding_start")),
            _dt(data.get("gate_close")),
            data.get("status") or "SCHEDULED",
            data.get("gate_id") or None,
            data.get("remarks") or None,
        ),
    )


def update_flight(flight_id, data):
    execute(
        """UPDATE flight SET
             flight_number=%s, route_id=%s, aircraft_id=%s,
             sched_departure=%s, sched_arrival=%s,
             boarding_start=%s, gate_close=%s,
             actual_departure=%s, actual_arrival=%s, status=%s,
             gate_id=%s, remarks=%s
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
            data.get("gate_id") or None,
            data.get("remarks") or None,
            flight_id,
        ),
    )


def delete_flight(flight_id):
    execute("DELETE FROM flight WHERE flight_id=%s", (flight_id,))


def assign_crew(flight_id, crew_id, role):
    execute(
        # Unassign is a soft delete, so re-assigning reactivates the existing row.
        """INSERT INTO crew_assignment (flight_id, crew_id, role) VALUES (%s, %s, %s)
           ON DUPLICATE KEY UPDATE role = VALUES(role), assigned_at = NOW(), unassigned_at = NULL""",
        (flight_id, crew_id, role),
    )


def unassign_crew(flight_id, crew_id):
    execute(
        "UPDATE crew_assignment SET unassigned_at = NOW() WHERE flight_id=%s AND crew_id=%s",
        (flight_id, crew_id),
    )
