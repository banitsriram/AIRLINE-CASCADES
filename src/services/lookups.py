"""Shared dropdown lookups. Every function returns rows shaped {id, label}."""

from src.db import query


def airports():
    return query(
        "SELECT airport_id AS id, CONCAT(iata_code, ' — ', city) AS label "
        "FROM airport ORDER BY iata_code"
    )


def aircraft_types():
    return query(
        "SELECT type_id AS id, CONCAT(manufacturer, ' ', model) AS label "
        "FROM aircraft_type ORDER BY manufacturer, model"
    )


def aircraft():
    return query(
        "SELECT aircraft_id AS id, registration AS label "
        "FROM aircraft WHERE status <> 'RETIRED' ORDER BY registration"
    )


def routes():
    return query(
        """SELECT r.route_id AS id, CONCAT(o.iata_code, ' → ', d.iata_code) AS label
           FROM route r
           JOIN airport o ON o.airport_id = r.origin_airport_id
           JOIN airport d ON d.airport_id = r.dest_airport_id
           WHERE r.deactivated_at IS NULL
           ORDER BY o.iata_code, d.iata_code"""
    )


def delay_reasons():
    return query(
        "SELECT reason_id AS id, CONCAT(category, ': ', description) AS label "
        "FROM delay_reason ORDER BY category"
    )


def crew():
    return query(
        "SELECT crew_id AS id, CONCAT(name, ' (', role, ')') AS label "
        "FROM crew WHERE terminated_at IS NULL ORDER BY name"
    )
