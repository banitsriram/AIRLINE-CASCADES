from src.db import query, execute, call_proc


def list_crew(role=None):
    sql = """SELECT c.crew_id, c.name, c.role, c.hire_date, c.terminated_at, a.iata_code AS base
              FROM crew c JOIN airport a ON a.airport_id = c.base_airport_id WHERE 1=1"""
    params = []
    if role:
        sql += " AND c.role = %s"
        params.append(role)
    sql += " ORDER BY c.name"
    return query(sql, params)


def get_crew(crew_id):
    rows = query(
        """SELECT c.*, a.iata_code AS base
           FROM crew c JOIN airport a ON a.airport_id = c.base_airport_id
           WHERE c.crew_id=%s""",
        (crew_id,),
    )
    return rows[0] if rows else None


def create_crew(data):
    return execute(
        "INSERT INTO crew (name, role, base_airport_id, hire_date) VALUES (%s,%s,%s,%s)",
        (data["name"], data["role"], data["base_airport_id"], data["hire_date"]),
    )


def update_crew(crew_id, data):
    execute(
        """UPDATE crew SET name=%s, role=%s, base_airport_id=%s, hire_date=%s, terminated_at=%s
           WHERE crew_id=%s""",
        (
            data["name"],
            data["role"],
            data["base_airport_id"],
            data["hire_date"],
            data.get("terminated_at") and data["terminated_at"].replace("T", " ") or None,
            crew_id,
        ),
    )


def delete_crew(crew_id):
    execute("DELETE FROM crew WHERE crew_id=%s", (crew_id,))


def certifications(crew_id):
    return query(
        """SELECT cc.type_id, at.model, at.manufacturer, cc.certified_date, cc.expiry_date
           FROM crew_certification cc
           JOIN aircraft_type at ON at.type_id = cc.type_id
           WHERE cc.crew_id=%s ORDER BY at.model""",
        (crew_id,),
    )


def add_certification(crew_id, type_id, certified_date, expiry_date):
    execute(
        """INSERT INTO crew_certification (crew_id, type_id, certified_date, expiry_date)
           VALUES (%s,%s,%s,%s)""",
        (crew_id, type_id, certified_date, expiry_date),
    )


def remove_certification(crew_id, type_id):
    execute(
        "DELETE FROM crew_certification WHERE crew_id=%s AND type_id=%s",
        (crew_id, type_id),
    )


def duty_status():
    return query(
        """SELECT c.crew_id, c.name, c.role, dl.duty_date, dl.hours_on_duty, dl.hours_flown,
                  ROUND(11 - dl.hours_on_duty, 2) AS hours_remaining
           FROM crew c JOIN duty_log dl ON dl.crew_id = c.crew_id
           WHERE dl.duty_date = CURDATE() AND dl.hours_on_duty >= 8
           ORDER BY dl.hours_on_duty DESC"""
    )


def replacement_crew(flight_id):
    result_sets = call_proc("find_replacement_crew", (flight_id,))
    return result_sets[0] if result_sets else []
