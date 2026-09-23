"""Simulates an examiner changing tables by hand in the MySQL client, then checks
the website reflects each change. Rebuilds the database at the end.

    python tests/test_live_changes.py
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app import app  # noqa: E402

env = dict(l.strip().split("=", 1) for l in open(os.path.join(ROOT, ".env")) if "=" in l)
c = app.test_client()


def mysql(sql):
    """Run SQL in a separate mysql client session, like an examiner would."""
    subprocess.run(
        ["mysql", "-h", env["DB_HOST"], "-u", env["DB_USER"], f"-p{env['DB_PASSWORD']}", env["DB_NAME"], "-e", sql],
        check=True, stderr=subprocess.DEVNULL,
    )


def page(url, status=200):
    r = c.get(url)
    assert r.status_code == status, (url, r.status_code)
    return r.get_data(as_text=True)


checks = []


def check(name, cond):
    checks.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)


try:
    # 1. INSERT a row
    mysql("INSERT INTO passenger (name, passport_no, email, phone, date_of_birth) "
          "VALUES ('Viva Examiner', 'X9999999', 'viva@example.com', '9000000000', '1980-05-05')")
    check("inserted passenger appears in search", "Viva Examiner" in page("/passengers/?q=Viva"))
    check("schema row count is exact after INSERT", ">2,001<" in page("/schema/").replace(" ", "") or "2001" in page("/schema/"))

    # 2. UPDATE rows
    mysql("UPDATE flight SET delay_minutes = 95 WHERE flight_number = 'AI-101' AND DATE(sched_departure) = CURDATE() + INTERVAL 1 DAY")
    html = page("/flights/?q=AI-101&status=DELAYED")
    check("hand-set delay shows as DELAYED with new time", "AI-101" in html and "DELAYED" in html)
    mysql("UPDATE airport SET runway_slots_per_hour = 9, min_connect_min = 50 WHERE iata_code = 'DEL'")
    check("airport rule change shows on its board", "9 departures an hour" in page("/airports/1/board"))

    # 3. ALTER TABLE ... ADD COLUMN
    mysql("ALTER TABLE passenger ADD COLUMN nationality VARCHAR(40) DEFAULT 'Indian'")
    check("new passenger column shows on the passenger page", "nationality" in page("/passengers/1"))
    mysql("ALTER TABLE airport ADD COLUMN elevation_m INT NULL")
    check("new airport column shows in admin list", "Elevation m" in page("/admin/airport/"))
    check("new airport column is editable", 'name="elevation_m"' in page("/admin/airport/1/edit"))
    form = {"iata_code": "DEL", "icao_code": "VIDP", "city": "Delhi", "country": "India", "timezone": "Asia/Kolkata",
            "open_time": "", "close_time": "", "runway_slots_per_hour": "9", "min_connect_min": "50",
            "min_turnaround_min": "60", "elevation_m": "216"}
    c.post("/admin/airport/1/edit", data=form)
    check("value saved into the new column", ">216<" in page("/admin/airport/"))

    # 4. ALTER an ENUM
    mysql("ALTER TABLE flight MODIFY status ENUM('SCHEDULED','BOARDING','DEPARTED','ARRIVED','CANCELLED','DIVERTED','ON_HOLD') "
          "DEFAULT 'SCHEDULED' NOT NULL")
    check("new ENUM value offered in the flight form", 'value="ON_HOLD"' in page("/flights/new"))
    mysql("UPDATE flight SET status = 'ON_HOLD' WHERE flight_number = 'AI-102' AND DATE(sched_departure) = CURDATE() + INTERVAL 2 DAY")
    check("flight in the new status displays it", "ON HOLD" in page("/flights/?status=ON_HOLD"))
    mysql("ALTER TABLE crew MODIFY role ENUM('CAPTAIN','FIRST_OFFICER','CABIN_CREW','PURSER','FLIGHT_ENGINEER') NOT NULL")
    check("new crew role offered in the crew form", 'value="FLIGHT_ENGINEER"' in page("/crew/new"))

    # 5. New rows in reference tables, new views
    mysql("INSERT INTO airport (iata_code, icao_code, city, country, timezone) VALUES ('IXZ','VOPB','Port Blair','India','Asia/Kolkata')")
    check("SQL-inserted airport appears on Airports", "Port Blair" in page("/airports/"))
    check("SQL-inserted airport appears on the dashboard map data", "Port Blair" in page("/"))
    mysql("CREATE VIEW v_viva_check AS SELECT flight_number, delay_minutes FROM flight WHERE delay_minutes > 0")
    check("new view listed on Schema", "v_viva_check" in page("/schema/"))
    check("new view's rows browsable", "AI-101" in page("/schema/v_viva_check/rows"))

    # 6. DELETE
    mysql("DELETE FROM passenger WHERE passport_no = 'X9999999'")
    check("deleted passenger is gone", "Viva Examiner" not in page("/passengers/?q=Viva"))

    # 7. Renamed columns: pages reading SELECT * adapt; pages naming the column report it
    mysql("ALTER TABLE passenger RENAME COLUMN email TO email_address")
    check("renamed column shows under its new name", "email_address" in page("/passengers/1"))
    mysql("ALTER TABLE booking RENAME COLUMN pnr TO pnr_code")
    html = page("/bookings/", status=500)
    check("breaking change gives a readable error page", "database rejected" in html and "pnr" in html)
finally:
    subprocess.run(["bash", os.path.join(ROOT, "scripts/setup_db.sh")], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

failed = [n for n, ok in checks if not ok]
print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed; database rebuilt.")
sys.exit(1 if failed else 0)
