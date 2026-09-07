from src.db import query
from src.services.crew import duty_status  # noqa: F401 (re-exported for reports.duty_status)


def ontime_performance():
    return query(
        """SELECT DATE(sched_departure) AS flight_date, COUNT(*) AS total_flights,
                  SUM(CASE WHEN delay_minutes <= 15 THEN 1 ELSE 0 END) AS on_time_flights,
                  ROUND(100 * SUM(CASE WHEN delay_minutes <= 15 THEN 1 ELSE 0 END) / COUNT(*), 1) AS on_time_pct
           FROM flight WHERE status <> 'CANCELLED'
           GROUP BY DATE(sched_departure) ORDER BY flight_date"""
    )


def top_delay_causes():
    return query(
        """SELECT dr.category, COUNT(*) AS delay_count, SUM(fd.minutes) AS total_minutes,
                  ROUND(AVG(fd.minutes), 1) AS avg_minutes
           FROM flight_delay fd JOIN delay_reason dr ON dr.reason_id = fd.reason_id
           GROUP BY dr.category ORDER BY delay_count DESC"""
    )


def load_factor():
    return query(
        """SELECT f.flight_id, f.flight_number, f.sched_departure, at.seat_capacity,
                  COUNT(t.ticket_id) AS tickets_sold,
                  ROUND(100 * COUNT(t.ticket_id) / at.seat_capacity, 1) AS load_factor_pct
           FROM flight f
           JOIN aircraft a ON a.aircraft_id = f.aircraft_id
           JOIN aircraft_type at ON at.type_id = a.type_id
           LEFT JOIN (
             SELECT t.ticket_id, t.flight_id FROM ticket t
             JOIN booking b ON b.booking_id = t.booking_id WHERE b.status <> 'CANCELLED'
           ) t ON t.flight_id = f.flight_id
           GROUP BY f.flight_id, f.flight_number, f.sched_departure, at.seat_capacity
           ORDER BY f.sched_departure"""
    )


def aircraft_utilisation():
    return query(
        """SELECT a.aircraft_id, a.registration, at.model, COUNT(f.flight_id) AS flights_operated,
                  ROUND(SUM(TIMESTAMPDIFF(MINUTE, f.sched_departure, f.sched_arrival)) / 60, 1) AS scheduled_flight_hours,
                  ROUND(SUM(f.delay_minutes) / 60, 1) AS total_delay_hours
           FROM aircraft a JOIN aircraft_type at ON at.type_id = a.type_id
           LEFT JOIN flight f ON f.aircraft_id = a.aircraft_id AND f.status <> 'CANCELLED'
           GROUP BY a.aircraft_id, a.registration, at.model
           ORDER BY flights_operated DESC"""
    )
