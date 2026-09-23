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



def crew():
    return query(
        "SELECT crew_id AS id, CONCAT(name, ' (', role, ')') AS label "
        "FROM crew WHERE terminated_at IS NULL ORDER BY name"
    )


def gates(airport_id=None):
    sql = """SELECT g.gate_id AS id, CONCAT(a.iata_code, ' ', g.gate_code, ' (', g.terminal, ')') AS label
             FROM gate g JOIN airport a ON a.airport_id = g.airport_id"""
    params = ()
    if airport_id:
        sql += " WHERE g.airport_id = %s"
        params = (airport_id,)
    return query(sql + " ORDER BY a.iata_code, g.terminal, g.gate_id", params)


def delay_codes():
    """IATA codes with their category, ordered for a grouped <select>."""
    return query(
        """SELECT dc.code_id AS id, dc.iata_code, dc.description, dr.category
           FROM delay_code dc JOIN delay_reason dr ON dr.reason_id = dc.reason_id
           ORDER BY dr.category, dc.iata_code"""
    )
