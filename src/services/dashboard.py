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
        "flights_this_week": query("SELECT COUNT(*) AS n FROM flight")[0]["n"],
        "knock_on_flights": query("SELECT COUNT(DISTINCT flight_id) AS n FROM delay_impact")[0]["n"],
        "confirmed_bookings": query(
            "SELECT COUNT(*) AS n FROM booking WHERE status IN ('CONFIRMED', 'CHECKED_IN')"
        )[0]["n"],
    }


def recent_delays(limit=10):
    return query(
        """SELECT fd.delay_id, f.flight_number, dr.category, fd.minutes, fd.recorded_at,
                  (SELECT COUNT(DISTINCT di.flight_id) FROM delay_impact di WHERE di.delay_id = fd.delay_id) AS knock_on
           FROM flight_delay fd
           JOIN flight f ON f.flight_id = fd.flight_id
           JOIN delay_code dc ON dc.code_id = fd.code_id
           JOIN delay_reason dr ON dr.reason_id = dc.reason_id
           ORDER BY fd.recorded_at DESC
           LIMIT %s""",
        (limit,),
    )


def network_routes():
    """Undirected airport pairs with at least one scheduled flight, for the
    dashboard's network constellation."""
    return query(
        """SELECT DISTINCT LEAST(r.origin_airport_id, r.dest_airport_id) AS a,
                           GREATEST(r.origin_airport_id, r.dest_airport_id) AS b
           FROM route r WHERE EXISTS (SELECT 1 FROM flight f WHERE f.route_id = r.route_id)"""
    )
