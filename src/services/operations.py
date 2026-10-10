"""Running the operation forward and looking after passengers it strands:
advance_clock() and rebook_ticket() in 05_procedures.sql."""

import mysql.connector

from src.db import query, call_proc, call_proc_with_out

REBOOK_REASONS = ("MISSED_CONNECTION", "CANCELLATION", "PASSENGER_REQUEST")


def advance_clock(until):
    """Moves every flight whose boarding time, ETD or ETA is at or before
    `until` on to BOARDING, DEPARTED or ARRIVED. Returns the counts."""
    return call_proc("advance_clock", (until,))[0][0]


def rebook_ticket(ticket_id, reason):
    """Moves one ticket to the next flight on its route the passenger can make.
    Returns the new flight_id."""
    return call_proc_with_out("rebook_ticket", (ticket_id, reason, 0))[-1]


def stranded_tickets(flight_ids):
    """Onward tickets whose connection is broken, for the given flights (as the
    inbound or the onward leg)."""
    ids = list(flight_ids)
    if not ids:
        return []
    marks = ", ".join(["%s"] * len(ids))
    return query(
        f"""SELECT DISTINCT t.ticket_id, m.pnr, m.passenger_name, m.out_flight,
                   IF(fo.status = 'CANCELLED', 'CANCELLATION', 'MISSED_CONNECTION') AS reason
            FROM v_missed_connections m
            JOIN ticket t ON t.booking_id = m.booking_id AND t.flight_id = m.out_flight_id
            JOIN flight fo ON fo.flight_id = m.out_flight_id
            WHERE m.in_flight_id IN ({marks}) OR m.out_flight_id IN ({marks})""",
        ids + ids,
    )


def rebook_stranded(flight_ids):
    """Rebooks every broken connection touching these flights. Returns
    (rebooked, failures) where failures pairs each PNR with MySQL's reason."""
    rebooked, failures = 0, []
    for t in stranded_tickets(flight_ids):
        try:
            rebook_ticket(t["ticket_id"], t["reason"])
            rebooked += 1
        except mysql.connector.Error as e:
            failures.append((t["pnr"], e.msg))
    return rebooked, failures


def rebookings_for_booking(booking_id):
    return query(
        """SELECT rb.rebooking_id, rb.reason, rb.rebooked_at, rb.old_seat_no, rb.new_seat_no,
                  rb.old_flight_id, fo.flight_number AS old_flight, fo.sched_departure AS old_std,
                  rb.new_flight_id, fn.flight_number AS new_flight, fn.sched_departure AS new_std
           FROM rebooking rb
           JOIN ticket t ON t.ticket_id = rb.ticket_id
           LEFT JOIN flight fo ON fo.flight_id = rb.old_flight_id
           JOIN flight fn ON fn.flight_id = rb.new_flight_id
           WHERE t.booking_id = %s
           ORDER BY rb.rebooked_at, rb.rebooking_id""",
        (booking_id,),
    )


def clock_position():
    """The latest actual departure or arrival recorded, or None before anything
    has flown."""
    return query(
        """SELECT MAX(t) AS t FROM (SELECT MAX(actual_departure) AS t FROM flight
                                    UNION ALL SELECT MAX(actual_arrival) FROM flight) x"""
    )[0]["t"]
