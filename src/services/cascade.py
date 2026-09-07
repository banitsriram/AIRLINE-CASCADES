from src.db import query, call_proc


def simulate_delay(flight_id, minutes, reason_id):
    """Records the delay and iteratively cascades it to downstream flights
    sharing the same aircraft (see simulate_delay() in 05_procedures.sql)."""
    call_proc("simulate_delay", (flight_id, minutes, reason_id))


def analyse_cascade(flight_id):
    result_sets = call_proc("analyse_cascade", (flight_id,))
    return result_sets[0] if result_sets else []


def affected_passengers(flight_id):
    return query(
        """WITH RECURSIVE cascade_tree AS (
             SELECT flight_id FROM flight WHERE flight_id = %s
             UNION ALL
             SELECT f.flight_id FROM flight f
             JOIN cascade_tree ct ON f.parent_flight_id = ct.flight_id
           )
           SELECT DISTINCT p.passenger_id, p.name, p.email, t.flight_id, t.seat_no, t.class
           FROM cascade_tree ct
           JOIN ticket t ON t.flight_id = ct.flight_id
           JOIN booking b ON b.booking_id = t.booking_id AND b.status = 'CONFIRMED'
           JOIN passenger p ON p.passenger_id = b.passenger_id
           ORDER BY t.flight_id, p.name""",
        (flight_id,),
    )
