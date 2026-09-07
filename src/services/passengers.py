from src.db import query, execute


def list_passengers(search=None):
    sql = "SELECT passenger_id, name, passport_no, email, phone, date_of_birth FROM passenger WHERE 1=1"
    params = []
    if search:
        sql += " AND name LIKE %s"
        params.append(f"%{search}%")
    sql += " ORDER BY name"
    return query(sql, params)


def get_passenger(passenger_id):
    rows = query("SELECT * FROM passenger WHERE passenger_id=%s", (passenger_id,))
    return rows[0] if rows else None


def create_passenger(data):
    return execute(
        """INSERT INTO passenger (name, passport_no, email, phone, date_of_birth)
           VALUES (%s,%s,%s,%s,%s)""",
        (
            data["name"],
            data.get("passport_no") or None,
            data.get("email") or None,
            data.get("phone") or None,
            data["date_of_birth"],
        ),
    )


def update_passenger(passenger_id, data):
    execute(
        """UPDATE passenger SET name=%s, passport_no=%s, email=%s, phone=%s, date_of_birth=%s
           WHERE passenger_id=%s""",
        (
            data["name"],
            data.get("passport_no") or None,
            data.get("email") or None,
            data.get("phone") or None,
            data["date_of_birth"],
            passenger_id,
        ),
    )


def delete_passenger(passenger_id):
    execute("DELETE FROM passenger WHERE passenger_id=%s", (passenger_id,))


def bookings_for_passenger(passenger_id):
    return query(
        "SELECT booking_id, pnr, booking_date, status FROM booking "
        "WHERE passenger_id=%s ORDER BY booking_date DESC",
        (passenger_id,),
    )
