from src.db import query, execute, call_proc_with_out


def list_bookings(status=None):
    sql = """SELECT b.booking_id, b.pnr, b.status, b.booking_date, p.name AS passenger_name
              FROM booking b JOIN passenger p ON p.passenger_id = b.passenger_id WHERE 1=1"""
    params = []
    if status:
        sql += " AND b.status = %s"
        params.append(status)
    sql += " ORDER BY b.booking_date DESC"
    return query(sql, params)


def get_booking(booking_id):
    rows = query(
        """SELECT b.*, p.name AS passenger_name
           FROM booking b JOIN passenger p ON p.passenger_id = b.passenger_id
           WHERE b.booking_id=%s""",
        (booking_id,),
    )
    return rows[0] if rows else None


def get_booking_id_by_pnr(pnr):
    rows = query("SELECT booking_id FROM booking WHERE pnr=%s", (pnr,))
    return rows[0]["booking_id"] if rows else None


def tickets_for_booking(booking_id):
    return query(
        """SELECT t.ticket_id, t.flight_id, ft.flight_number, ft.origin, ft.dest, ft.etd,
                  ft.status AS flight_status, ft.display_status, t.seat_no, t.fare, t.class,
                  t.checked_in_at, t.boarded_at
           FROM ticket t JOIN v_flight_times ft ON ft.flight_id = t.flight_id
           WHERE t.booking_id=%s
           ORDER BY ft.std""",
        (booking_id,),
    )


def book_ticket(passenger_id, flight_id, seat_no, ticket_class, fare):
    """Creates a new booking + its first ticket atomically via book_ticket()
    (05_procedures.sql). Returns the new booking_id."""
    result = call_proc_with_out(
        "book_ticket", (passenger_id, flight_id, seat_no, ticket_class, fare, "")
    )
    pnr = result[5]
    return get_booking_id_by_pnr(pnr)


def add_ticket(booking_id, flight_id, seat_no, ticket_class, fare):
    execute(
        """INSERT INTO ticket (booking_id, flight_id, seat_no, fare, class)
           VALUES (%s,%s,%s,%s,%s)""",
        (booking_id, flight_id, seat_no, fare, ticket_class),
    )


def cancel_booking(booking_id):
    execute(
        "UPDATE booking SET status='CANCELLED', cancelled_at=NOW() WHERE booking_id=%s",
        (booking_id,),
    )


def check_in_ticket(ticket_id):
    execute("UPDATE ticket SET checked_in_at = NOW() WHERE ticket_id=%s", (ticket_id,))
