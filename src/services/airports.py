from src.db import query


def list_airports():
    return query(
        """SELECT a.*, (SELECT COUNT(*) FROM gate g WHERE g.airport_id = a.airport_id) AS gates,
                  (SELECT COUNT(*) FROM v_flight_times ft
                    WHERE ft.origin_airport_id = a.airport_id AND DATE(ft.std) = CURDATE()) AS departures_today,
                  (SELECT COUNT(*) FROM v_flight_times ft
                    WHERE ft.origin_airport_id = a.airport_id AND ft.display_status = 'DELAYED') AS delayed_departures
           FROM airport a ORDER BY a.airport_id"""
    )


def get_airport(airport_id):
    rows = query("SELECT * FROM airport WHERE airport_id=%s", (airport_id,))
    return rows[0] if rows else None


def departures(airport_id, date):
    return query(
        """SELECT * FROM v_flight_times WHERE origin_airport_id=%s AND DATE(std)=%s ORDER BY std""",
        (airport_id, date),
    )


def arrivals(airport_id, date):
    return query(
        """SELECT * FROM v_flight_times WHERE dest_airport_id=%s AND DATE(sta)=%s ORDER BY sta""",
        (airport_id, date),
    )


def board_dates():
    return [r["d"] for r in query("SELECT DISTINCT DATE(sched_departure) AS d FROM flight ORDER BY d")]
