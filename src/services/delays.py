"""Delay notices and their organisation-wide impact. Filing a notice runs the
cascade engine, simulate_delay() in 05_procedures.sql."""

from src.db import query, execute, call_proc, call_proc_with_out

NOTICE_FIELDS = (
    "minutes", "code_id", "sub_reason", "phase", "ops_status", "new_gate_id",
    "new_boarding_time", "pax_deboarded", "swap_aircraft_id", "announcement",
    "meal_voucher", "compensation_eligible", "rebooking_offered", "reported_by", "remarks",
)

# Non-timing fields that can be edited after filing. Changing minutes would
# leave the recorded cascade inconsistent, so that means filing another notice.
EDITABLE_FIELDS = (
    "sub_reason", "announcement", "pax_deboarded", "meal_voucher", "compensation_eligible",
    "rebooking_offered", "reported_by", "remarks",
)


def file_delay(flight_id, notice):
    """Files the notice and cascades it. Returns the new delay_id."""
    args = (flight_id,) + tuple(notice[f] for f in NOTICE_FIELDS) + (0,)
    return call_proc_with_out("simulate_delay", args)[-1]


def get_delay(delay_id):
    rows = query(
        """SELECT fd.*, dr.category, dc.iata_code, dc.description AS code_description,
                  ft.flight_number, ft.origin, ft.dest, ft.std, ft.etd, ft.eta, ft.display_status,
                  ng.gate_code AS new_gate_code, sa.registration AS swap_registration
           FROM flight_delay fd
           JOIN delay_code dc ON dc.code_id = fd.code_id
           JOIN delay_reason dr ON dr.reason_id = dc.reason_id
           JOIN v_flight_times ft ON ft.flight_id = fd.flight_id
           LEFT JOIN gate ng ON ng.gate_id = fd.new_gate_id
           LEFT JOIN aircraft sa ON sa.aircraft_id = fd.swap_aircraft_id
           WHERE fd.delay_id = %s""",
        (delay_id,),
    )
    return rows[0] if rows else None


def list_delays(open_only=False):
    sql = """SELECT fd.delay_id, fd.flight_id, ft.flight_number, ft.origin, ft.dest, ft.std,
                    dr.category, dc.iata_code, fd.minutes, fd.ops_status, fd.reported_by,
                    fd.recorded_at, fd.resolved_at,
                    (SELECT COUNT(DISTINCT di.flight_id) FROM delay_impact di WHERE di.delay_id = fd.delay_id) AS knock_on_flights,
                    (SELECT COALESCE(SUM(di.minutes_added), 0) FROM delay_impact di
                      WHERE di.delay_id = fd.delay_id) AS knock_on_minutes
             FROM flight_delay fd
             JOIN v_flight_times ft ON ft.flight_id = fd.flight_id
             JOIN delay_code dc ON dc.code_id = fd.code_id
             JOIN delay_reason dr ON dr.reason_id = dc.reason_id"""
    if open_only:
        sql += " WHERE fd.resolved_at IS NULL"
    return query(sql + " ORDER BY fd.recorded_at DESC, fd.delay_id DESC")


def impacts(delay_id):
    return query(
        """SELECT di.impact_id, di.link, di.minutes_added, di.old_etd, di.new_etd, di.pass_no,
                  ft.flight_id, ft.flight_number, ft.origin, ft.dest, ft.registration,
                  ft.std, ft.etd, ft.delay_minutes, ft.gate_code,
                  cf.flight_id AS cause_flight_id, cf.flight_number AS cause_flight
           FROM delay_impact di
           JOIN v_flight_times ft ON ft.flight_id = di.flight_id
           LEFT JOIN flight cf ON cf.flight_id = di.cause_flight_id
           WHERE di.delay_id = %s
           ORDER BY di.pass_no, di.new_etd""",
        (delay_id,),
    )


def _in(ids):
    return ", ".join(["%s"] * len(ids))


def affected_summary(flight_ids):
    """Operational fallout for a set of flights, read from the flag views."""
    ids = list(flight_ids)
    if not ids:
        return {"missed": [], "duty": [], "curfew": [], "passengers": 0, "aircraft": 0, "airports": 0}
    return {
        "missed": query(
            f"""SELECT * FROM v_missed_connections
                WHERE in_flight_id IN ({_in(ids)}) OR out_flight_id IN ({_in(ids)})
                ORDER BY in_eta""",
            ids + ids,
        ),
        "duty": query(
            f"""SELECT DISTINCT b.* FROM v_duty_breaches b
                JOIN crew_assignment ca ON ca.crew_id = b.crew_id AND ca.unassigned_at IS NULL
                JOIN flight f ON f.flight_id = ca.flight_id AND DATE(f.sched_departure) = b.duty_date
                WHERE ca.flight_id IN ({_in(ids)})
                ORDER BY b.duty_hours DESC""",
            ids,
        ),
        "curfew": query(f"SELECT * FROM v_curfew_risk WHERE flight_id IN ({_in(ids)})", ids),
        "passengers": query(
            f"""SELECT COUNT(DISTINCT b.passenger_id) AS n FROM ticket t
                JOIN booking b ON b.booking_id = t.booking_id AND b.status IN ('CONFIRMED', 'CHECKED_IN')
                WHERE t.flight_id IN ({_in(ids)})""",
            ids,
        )[0]["n"],
        "aircraft": query(
            f"SELECT COUNT(DISTINCT aircraft_id) AS n FROM flight WHERE flight_id IN ({_in(ids)})", ids
        )[0]["n"],
        "airports": query(
            f"""SELECT COUNT(DISTINCT r.origin_airport_id) AS n FROM flight f
                JOIN route r ON r.route_id = f.route_id WHERE f.flight_id IN ({_in(ids)})""",
            ids,
        )[0]["n"],
    }


def update_notice(delay_id, notice):
    execute(
        f"UPDATE flight_delay SET {', '.join(f'{f}=%s' for f in EDITABLE_FIELDS)} WHERE delay_id=%s",
        tuple(notice[f] for f in EDITABLE_FIELDS) + (delay_id,),
    )


def resolve(delay_id):
    execute("UPDATE flight_delay SET resolved_at = NOW() WHERE delay_id=%s AND resolved_at IS NULL", (delay_id,))


def reset_all():
    call_proc("reset_all_delays")


def network_flags():
    return {
        "missed": query("SELECT COUNT(*) AS n FROM v_missed_connections")[0]["n"],
        "duty": query("SELECT COUNT(*) AS n FROM v_duty_breaches")[0]["n"],
        "curfew": query("SELECT COUNT(*) AS n FROM v_curfew_risk")[0]["n"],
    }
