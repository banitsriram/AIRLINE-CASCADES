from src.db import query


def summary():
    return {
        "flights_today": query(
            "SELECT COUNT(*) AS n FROM flight WHERE DATE(sched_departure) = CURDATE()"
        )[0]["n"],
        "delayed_now": query(
            "SELECT COUNT(*) AS n FROM flight "
            "WHERE delay_minutes > 0 AND status NOT IN ('ARRIVED', 'CANCELLED')"
        )[0]["n"],
        "active_aircraft": query(
            "SELECT COUNT(*) AS n FROM aircraft WHERE status = 'ACTIVE'"
        )[0]["n"],
        "crew_on_duty": query(
            "SELECT COUNT(DISTINCT crew_id) AS n FROM duty_log WHERE duty_date = CURDATE()"
        )[0]["n"],
        "confirmed_bookings": query(
            "SELECT COUNT(*) AS n FROM booking WHERE status IN ('CONFIRMED', 'CHECKED_IN')"
        )[0]["n"],
    }


def recent_delays(limit=10):
    return query(
        """SELECT fd.delay_id, f.flight_number, dr.category, fd.minutes, fd.recorded_at
           FROM flight_delay fd
           JOIN flight f ON f.flight_id = fd.flight_id
           JOIN delay_reason dr ON dr.reason_id = fd.reason_id
           ORDER BY fd.recorded_at DESC
           LIMIT %s""",
        (limit,),
    )
