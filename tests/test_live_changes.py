"""Someone changes tables by hand in the MySQL client while the site is
running; each change must show on the next page load (or, if it breaks a page,
give MySQL's own error rather than a stack trace)."""
import os
import subprocess

from src.config import Settings

from conftest import rebuild_database


def mysql(sql):
    """Run SQL in a separate mysql client session, as a person at a terminal would."""
    subprocess.run(
        ["mysql", "--protocol=TCP", "-h", Settings.DB_HOST, "-P", str(Settings.DB_PORT),
         "-u", Settings.DB_USER, Settings.DB_NAME, "-e", sql],
        check=True, stderr=subprocess.DEVNULL, env={**os.environ, "MYSQL_PWD": Settings.DB_PASSWORD},
    )


def test_hand_made_changes_show_on_the_site(client):
    checks = []

    def check(name, cond):
        checks.append((name, bool(cond)))

    def page(url, status=200):
        r = client.get(url)
        assert r.status_code == status, (url, r.status_code)
        return r.get_data(as_text=True)

    try:
        # 1. INSERT a row
        mysql("INSERT INTO passenger (name, passport_no, email, phone, date_of_birth) "
              "VALUES ('Manual Entry', 'X9999999', 'manual@example.com', '9000000000', '1980-05-05')")
        check("inserted passenger appears in search", "Manual Entry" in page("/passengers/?q=Manual"))
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
        client.post("/admin/airport/1/edit", data=form)
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
        mysql("CREATE VIEW v_manual_check AS SELECT flight_number, delay_minutes FROM flight WHERE delay_minutes > 0")
        check("new view listed on Schema", "v_manual_check" in page("/schema/"))
        check("new view's rows browsable", "AI-101" in page("/schema/v_manual_check/rows"))

        # 6. DELETE
        mysql("DELETE FROM passenger WHERE passport_no = 'X9999999'")
        check("deleted passenger is gone", "Manual Entry" not in page("/passengers/?q=Manual"))

        # 7. Renamed columns: pages reading SELECT * adapt; pages naming the column report it
        mysql("ALTER TABLE passenger RENAME COLUMN email TO email_address")
        check("renamed column shows under its new name", "email_address" in page("/passengers/1"))
        mysql("ALTER TABLE booking RENAME COLUMN pnr TO pnr_code")
        html = page("/bookings/", status=500)
        check("breaking change gives a readable error page", "database rejected" in html and "pnr" in html)
    finally:
        rebuild_database()

    failed = [name for name, ok in checks if not ok]
    assert not failed, failed
    assert len(checks) == 18
