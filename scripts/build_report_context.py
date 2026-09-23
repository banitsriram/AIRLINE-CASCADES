"""Builds docs/REPORT_CONTEXT.md: everything needed to write the project report,
filled with figures measured from the live project.

    python scripts/build_report_context.py

It rebuilds the database several times (scripts/setup_db.sh), runs a demo
cascade and every test, and leaves the database freshly seeded. Takes 1-2 min.
The narrative lives in scripts/report_template.md; {{PLACEHOLDERS}} there are
filled in here.
"""
import datetime
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
OUT = os.path.join(ROOT, "docs", "REPORT_CONTEXT.md")
ENV = dict(l.strip().split("=", 1) for l in open(os.path.join(ROOT, ".env")) if "=" in l and not l.startswith("#"))


def setup_db():
    subprocess.run(["bash", "scripts/setup_db.sh"], cwd=ROOT, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def mysql_table(sql_file):
    """Run a .sql file with the mysql client and return its boxed text output."""
    with open(os.path.join(ROOT, sql_file)) as f:
        r = subprocess.run(
            ["mysql", "--table", "-h", ENV["DB_HOST"], "-u", ENV["DB_USER"], f"-p{ENV['DB_PASSWORD']}", ENV["DB_NAME"]],
            stdin=f, capture_output=True, text=True,
        )
    return r.stdout.strip()


def md_table(rows, cols=None, fmt=None):
    if not rows:
        return "_(no rows)_"
    cols = cols or list(rows[0].keys())
    fmt = fmt or {}
    cell = lambda c, v: fmt[c](v) if c in fmt else ("NULL" if v is None else str(v).replace("|", "\\|"))
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(cell(c, r[c]) for c in cols) + " |" for r in rows]
    return "\n".join(lines)


def head_tail(text, n=12):
    lines = text.splitlines()
    return text if len(lines) <= n + 4 else "\n".join(lines[:n] + ["... (" + str(len(lines) - n - 1) + " more rows)", lines[-1]])


# ---------------------------------------------------------------- 1. fresh database, in-process measurements
print("Rebuilding database...")
setup_db()

from app import app  # noqa: E402  (imported after the rebuild so pooled connections see the new database)
from src.db import query, call_proc  # noqa: E402
from src.services import delays as delays_service  # noqa: E402

v = {"GENERATED_AT": datetime.datetime.now().strftime("%A %d %B %Y, %H:%M")}

base_tables = [r["t"] for r in query(
    "SELECT table_name t FROM information_schema.tables WHERE table_schema=DATABASE() AND table_type='BASE TABLE' ORDER BY table_name")]
views = [r["t"] for r in query("SELECT table_name t FROM information_schema.views WHERE table_schema=DATABASE() ORDER BY table_name")]
triggers = query("""SELECT trigger_name AS `Trigger`, action_timing AS `Timing`, event_manipulation AS `Event`,
                           event_object_table AS `Table` FROM information_schema.triggers
                    WHERE trigger_schema=DATABASE() ORDER BY trigger_name""")
routines = query("""SELECT routine_name AS `Procedure`, routine_type AS `Type`,
                           (SELECT COUNT(*) FROM information_schema.parameters p
                             WHERE p.specific_schema=r.routine_schema AND p.specific_name=r.routine_name) AS `Parameters`
                    FROM information_schema.routines r WHERE routine_schema=DATABASE() ORDER BY routine_name""")
v.update(N_TABLES=len(base_tables), N_VIEWS=len(views), N_TRIGGERS=len(triggers), N_ROUTINES=len(routines))
v["TRIGGERS_TABLE"] = md_table(triggers)
v["ROUTINES_TABLE"] = md_table(routines)

counts = [{"Table": t, "Rows": query(f"SELECT COUNT(*) n FROM `{t}`")[0]["n"]} for t in base_tables]
v["COUNTS_TABLE"] = md_table(counts, fmt={"Rows": lambda n: f"{n:,}"})
c = {r["Table"]: r["Rows"] for r in counts}
v["DATA_SUMMARY"] = (f"{c['airport']} airports, {c['gate']} gates, {c['aircraft']} aircraft, {c['route']} routes, "
                     f"{c['flight']:,} flights over 7 days, {c['crew']} crew, {c['passenger']:,} passengers, "
                     f"{c['booking']:,} bookings, {c['ticket']:,} tickets, {c['delay_code']} IATA delay codes")

facts = query("""SELECT
    (SELECT COUNT(*) FROM (SELECT booking_id FROM ticket GROUP BY booking_id HAVING COUNT(*) = 2) x) AS connecting_bookings,
    (SELECT COUNT(DISTINCT ca.flight_id) FROM crew_assignment ca JOIN flight f ON f.flight_id = ca.flight_id
       JOIN crew_assignment ca2 ON ca2.crew_id = ca.crew_id JOIN flight f2 ON f2.flight_id = ca2.flight_id
      WHERE f2.aircraft_id <> f.aircraft_id AND DATE(f2.sched_departure) = DATE(f.sched_departure)) AS crosslinked_flights,
    (SELECT MIN(sched_departure) FROM flight) AS first_dep, (SELECT MAX(sched_arrival) FROM flight) AS last_arr,
    (SELECT COUNT(*) FROM flight WHERE delay_minutes > 0) AS delayed_flights,
    (SELECT COUNT(*) FROM v_missed_connections) AS missed,
    (SELECT COUNT(*) FROM v_duty_breaches) AS duty,
    (SELECT COUNT(*) FROM v_curfew_risk) AS curfew""")[0]
status_mix = query("SELECT status, COUNT(*) n FROM flight GROUP BY status ORDER BY n DESC")
v["DATA_FACTS"] = "\n".join([
    f"- Schedule window: {facts['first_dep']:%a %d %b %Y %H:%M} to {facts['last_arr']:%a %d %b %Y %H:%M}.",
    f"- Flight status mix at generation time: " + ", ".join(f"{r['status']} {r['n']:,}" for r in status_mix) + ".",
    f"- Two-leg connecting bookings: {facts['connecting_bookings']:,}.",
    f"- Flights whose crew also fly a different aircraft the same day (cross-aircraft crew links): {facts['crosslinked_flights']:,}.",
    f"- With the 10 sample delays applied: {facts['delayed_flights']} flights late, {facts['missed']} missed connections, "
    f"{facts['duty']} crew duty breaches, {facts['curfew']} curfew risks.",
])

rules = query("""SELECT iata_code AS `IATA`, icao_code AS `ICAO`, city AS `City`,
                        IFNULL(CONCAT(TIME_FORMAT(open_time,'%H:%i'),'–',TIME_FORMAT(close_time,'%H:%i')),'24 h') AS `Hours`,
                        runway_slots_per_hour AS `Departures/hour`, min_connect_min AS `Min connection (min)`,
                        min_turnaround_min AS `Min turnaround (min)`,
                        (SELECT COUNT(*) FROM gate g WHERE g.airport_id = a.airport_id) AS `Gates`
                 FROM airport a ORDER BY airport_id""")
v["AIRPORT_RULES"] = md_table(rules)

# Column reference
parts = []
for t in base_tables + views:
    cols = query("""SELECT column_name c, column_type ty, is_nullable n, column_key k, column_default d, extra e
                    FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name=%s
                    ORDER BY ordinal_position""", (t,))
    fks = {r["c"]: r["ref"] for r in query("""SELECT column_name c, CONCAT(referenced_table_name,'.',referenced_column_name) ref
             FROM information_schema.key_column_usage WHERE table_schema=DATABASE() AND table_name=%s
             AND referenced_table_name IS NOT NULL""", (t,))}
    rows = []
    for col in cols:
        notes = []
        if col["c"] in fks:
            notes.append(f"FK → `{fks[col['c']]}`")
        extra = (col["e"] or "").replace("DEFAULT_GENERATED", "").strip()
        if extra:
            notes.append(extra)
        if col["d"] is not None:
            notes.append(f"default `{col['d']}`")
        rows.append({"Column": f"`{col['c']}`", "Type": f"`{col['ty']}`", "Null": col["n"],
                     "Key": col["k"] or "", "Notes": "; ".join(notes)})
    kind = "view" if t in views else f"table, {c.get(t, 0):,} rows"
    parts.append(f"#### `{t}` ({kind})\n\n" + md_table(rows))
v["COLUMNS"] = "\n\n".join(parts)

# Routes
routes = []
for r in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
    if r.endpoint == "static":
        continue
    routes.append({"Methods": ", ".join(sorted(m for m in r.methods if m in ("GET", "POST"))),
                   "URL": f"`{r.rule}`", "Endpoint": f"`{r.endpoint}`"})
v["N_ROUTES"] = len(routes)
v["ROUTES"] = md_table(routes)
v["N_TEMPLATES"] = sum(len([f for f in fs if f.endswith(".html")]) for _, _, fs in os.walk(os.path.join(ROOT, "templates")))

# Sample delays already in the seed
sample = query("""SELECT d.delay_id AS `#`, f.flight_number AS `Flight`, CONCAT(o.iata_code, '→', de.iata_code) AS `Route`,
                         dc.iata_code AS `IATA`, dr.category AS `Category`, d.sub_reason AS `Details`, d.minutes AS `Minutes`,
                         (SELECT COUNT(*) FROM delay_impact i WHERE i.delay_id = d.delay_id) AS `Other flights moved`,
                         (SELECT COALESCE(SUM(minutes_added), 0) FROM delay_impact i WHERE i.delay_id = d.delay_id) AS `Knock-on minutes`
                  FROM flight_delay d JOIN flight f USING (flight_id) JOIN route r ON r.route_id = f.route_id
                  JOIN airport o ON o.airport_id = r.origin_airport_id JOIN airport de ON de.airport_id = r.dest_airport_id
                  JOIN delay_code dc USING (code_id) JOIN delay_reason dr ON dr.reason_id = dc.reason_id
                  ORDER BY d.delay_id""")
filed = sum(r["Minutes"] for r in sample)
knock = sum(int(r["Knock-on minutes"]) for r in sample)
links = query("SELECT link, COUNT(*) n FROM delay_impact GROUP BY link ORDER BY n DESC")
v["SAMPLE_DELAYS"] = md_table(sample) + "\n\n" + (
    f"**Totals:** {filed} minutes filed directly caused **{knock:,} knock-on minutes** across "
    f"{sum(int(r['Other flights moved']) for r in sample)} other flight changes, a reactionary-to-primary ratio "
    f"of about **{knock / filed:.1f} : 1**. Knock-on changes by link: "
    + ", ".join(f"{r['link']} {r['n']}" for r in links) + ".")

# Report query outputs
qparts = []
for q, title in [("q3_ontime_performance", "q3 on-time performance"), ("q4_top_delay_causes", "q4 delay causes"),
                 ("q6_load_factor", "q6 load factor (first rows)"), ("q7_duty_status", "q7 crew duty status"),
                 ("q8_aircraft_utilisation", "q8 aircraft utilisation (first rows)")]:
    qparts.append(f"**{title}** (`database/queries/{q}.sql`)\n\n```\n{head_tail(mysql_table(f'database/queries/{q}.sql')) or '(empty result)'}\n```")
v["QUERY_RESULTS"] = "\n\n".join(qparts)

# Route smoke test (GET only; changes nothing)
client = app.test_client()
ids = query("""SELECT (SELECT MIN(flight_id) FROM flight) f, (SELECT MIN(delay_id) FROM flight_delay) d,
                      (SELECT MIN(crew_id) FROM crew) c, (SELECT MIN(passenger_id) FROM passenger) p,
                      (SELECT MIN(booking_id) FROM booking) b, (SELECT MIN(airport_id) FROM airport) a""")[0]
from src.services import admin as admin_service  # noqa: E402

urls = ["/", "/flights/", "/flights/?status=DELAYED", "/flights/?q=DEL", f"/flights/{ids['f']}", f"/flights/{ids['f']}/edit",
        "/flights/new", f"/flights/{ids['f']}/delay", "/delays/", "/delays/?open=1", f"/delays/{ids['d']}",
        f"/delays/{ids['d']}/edit", "/delays/reset", "/airports/", f"/airports/{ids['a']}/board", "/cascade/",
        f"/cascade/{ids['f']}", "/crew/", "/crew/duty", f"/crew/{ids['c']}", f"/crew/{ids['c']}/edit", "/crew/new",
        f"/crew/replacement/{ids['f']}", "/passengers/", f"/passengers/{ids['p']}", f"/passengers/{ids['p']}/edit",
        "/passengers/new", "/bookings/", f"/bookings/{ids['b']}", "/bookings/new", "/reports/", "/reports/ontime",
        "/reports/delay-causes", "/reports/load-factor", "/reports/duty-status", "/reports/utilisation", "/admin/", "/schema/"]
for e in admin_service.ENTITIES:
    urls += [f"/admin/{e}/", f"/admin/{e}/new", f"/admin/{e}/1/edit"]
for t in base_tables + views:
    urls += [f"/schema/{t}", f"/schema/{t}/rows"]
bad = [(u, s) for u in urls if (s := client.get(u).status_code) >= 400]
smoke = f"{len(urls) - len(bad)}/{len(urls)} pages returned successfully" + (f"; failures: {bad}" if bad else "")

# Worked cascade on a clean network
call_proc("reset_all_delays")
flight = query("""SELECT ft.flight_id, ft.flight_number, ft.origin, ft.dest, ft.registration, ft.std
                  FROM v_flight_times ft WHERE ft.aircraft_id = 1 AND ft.status = 'SCHEDULED'
                    AND DATE(ft.std) = CURDATE() + INTERVAL 1 DAY ORDER BY ft.std LIMIT 1""")[0]
code_id = query("SELECT code_id FROM delay_code WHERE iata_code = '41'")[0]["code_id"]
notice = {f: None for f in delays_service.NOTICE_FIELDS}
notice.update(minutes=180, code_id=code_id, sub_reason="Hydraulic leak found on walk-around", phase="AT_GATE",
              ops_status="DELAYED", reported_by="R. Mehta (Duty Manager DEL)", pax_deboarded=False,
              meal_voucher=True, compensation_eligible=True, rebooking_offered=False,
              announcement=f"Flight {flight['flight_number']} is delayed by 180 minutes.")
t0 = time.perf_counter()
delay_id = delays_service.file_delay(flight["flight_id"], notice)
elapsed = time.perf_counter() - t0
impacts = delays_service.impacts(delay_id)
affected = {flight["flight_id"]} | {i["flight_id"] for i in impacts}
summary = delays_service.affected_summary(affected)
after = query("SELECT etd FROM v_flight_times WHERE flight_id = %s", (flight["flight_id"],))[0]["etd"]
imp_rows = [{"Pass": i["pass_no"], "Flight": i["flight_number"], "Route": f"{i['origin']}→{i['dest']}",
             "Aircraft": i["registration"], "Link": i["link"], "Caused by": i["cause_flight"] or f"{i['origin']} runway slot",
             "ETD before": f"{i['old_etd']:%a %H:%M}", "ETD after": f"{i['new_etd']:%a %H:%M}", "Added": f"+{i['minutes_added']}"}
            for i in impacts]
missed_rows = [{"PNR": m["pnr"], "Passenger": m["passenger_name"], "Inbound": m["in_flight"], "Onward": m["out_flight"],
                "At": m["connect_airport"], "Connection": f"{m['connect_min']} min", "Needs": f"{m['min_connect_min']} min"}
               for m in summary["missed"]]
by_link = {}
for i in impacts:
    by_link[i["link"]] = by_link.get(i["link"], 0) + 1
v["DEMO_CASCADE"] = "\n".join([
    f"**Scenario:** starting from a network with no delays, file a 180-minute delay on **{flight['flight_number']} "
    f"({flight['origin']} → {flight['dest']}, aircraft {flight['registration']}, STD {flight['std']:%a %d %b %H:%M})** "
    f"with IATA code 41 (aircraft defect), \"Hydraulic leak found on walk-around\", phase At gate.",
    "",
    f"**Result:** the engine ran in **{elapsed:.2f} s** over all {c['flight']:,} flights and made "
    f"**{len(impacts)} knock-on changes** in {max((i['pass_no'] for i in impacts), default=0)} passes "
    f"({', '.join(f'{k} {n}' for k, n in sorted(by_link.items()))}), totalling "
    f"{sum(i['minutes_added'] for i in impacts)} knock-on minutes. {flight['flight_number']}'s ETD moved to "
    f"{after:%a %H:%M}. It reached {summary['aircraft']} aircraft and {summary['airports']} airports, "
    f"affected {summary['passengers']} passengers and broke {len(summary['missed'])} connections "
    f"({len(summary['duty'])} duty breaches, {len(summary['curfew'])} curfew risks).",
    "",
    "Every knock-on change, as logged in `delay_impact`:",
    "",
    md_table(imp_rows),
    "",
    "Passengers who now miss connections (from `v_missed_connections`; a negative connection means the onward "
    "flight now leaves before the inbound lands):",
    "",
    md_table(missed_rows),
    "",
    "How to read it: AIRCRAFT rows follow the same aircraft's day; a CREW row is where crew arriving late are "
    "rostered onto a different aircraft, so the delay jumps aircraft; SLOT rows are flights pushed into the next "
    "hour because the airport's departures for that hour were full.",
])

# ---------------------------------------------------------------- 2. test suite (each on a fresh database)
results = [f"- **Route smoke test:** {smoke}."]
for test in ["tests/test_cascade.py", "tests/test_crew_assignment.py", "tests/test_live_changes.py"]:
    print("Running", test)
    setup_db()
    r = subprocess.run([sys.executable, test], cwd=ROOT, capture_output=True, text=True)
    lines = [l for l in r.stdout.splitlines() if l.strip()]
    status = "PASS" if r.returncode == 0 else f"FAIL (exit {r.returncode})"
    if test.endswith("live_changes.py"):
        results.append(f"- **`{test}`: {status}**\n\n```\n" + "\n".join(lines) + "\n```")
    else:
        results.append(f"- **`{test}`: {status}**, output: `{lines[-1] if lines else ''}`")
v["TEST_RESULTS"] = "\n".join(results)

print("Rebuilding database (leave it clean)...")
setup_db()

# ---------------------------------------------------------------- 3. repository facts
git = subprocess.run(["git", "log", "--format=%h|%ad|%s", "--date=format:%d %b %Y %H:%M"],
                     cwd=ROOT, capture_output=True, text=True).stdout.strip().splitlines()
v["GIT_LOG"] = md_table([dict(zip(["Commit", "Date", "Message"], l.split("|", 2))) for l in git]) + \
    "\n\n(Work after the last commit is in the working tree when this file was generated.)"

SKIP_DIRS = {"venv", ".venv", ".git", "__pycache__", "screenshots", ".playwright-mcp", ".claude"}
EXT_LANG = {".sql": "sql", ".py": "python", ".html": "html", ".css": "css", ".js": "javascript",
            ".sh": "bash", ".md": "markdown", ".txt": "text", ".example": "bash", ".gitignore": "text"}
files = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
    for fn in sorted(filenames):
        rel = os.path.relpath(os.path.join(dirpath, fn), ROOT)
        if fn == ".env" or rel in (os.path.relpath(OUT, ROOT), "docs/REPORT_CONTEXT_CORE.md", "scripts/report_template.md") \
                or fn.endswith((".pyc", ".png", ".DS_Store")):
            continue
        ext = os.path.splitext(fn)[1] or fn
        if ext in EXT_LANG or fn in (".gitignore", ".env.example"):
            files.append(rel)

loc = []
for rel in files:
    if rel.startswith("docs/") or rel.endswith(".md"):
        continue
    n = sum(1 for _ in open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace"))
    loc.append({"File": f"`{rel}`", "Lines": n})
loc.sort(key=lambda r: r["File"])
v["LOC_TOTAL"] = f"{sum(r['Lines'] for r in loc):,}"
v["LOC_TABLE"] = md_table(loc) + f"\n\n**Total: {v['LOC_TOTAL']} lines** (excluding documentation)."

SHOTS = {
    "01-dashboard": "Dashboard: live headline, date, summary and the network constellation map",
    "02-dashboard-map-hover": "Map interaction: hovering Delhi draws its 19 routes and shows its tooltip",
    "03-dashboard-full": "Full dashboard: figures, airport-board shortcuts, recent delays",
    "04-flights-delayed": "Flights filtered to Delayed: scheduled times struck through, estimates in amber",
    "05-flight-detail": "Flight detail: times, crew assignment, delays filed, knock-on received, all columns",
    "06-delay-form": "Delay form filled in: IATA code, 180 minutes, auto-filled ETD/ETA/boarding, announcement, vouchers",
    "07-delay-log": "Delay log: every notice with its knock-on count and minutes",
    "08-airports": "Airports: operating rules, gates, departures today, late departures",
    "09-airport-board": "Delhi departure and arrival board with the day picker (carousel dots)",
    "10-crew-profile": "Crew profile (Team Member Card): role, name, certifications",
    "11-passengers": "Passengers list with the Section Headline Block",
    "12-booking-connection": "A two-leg connecting booking with its tickets",
    "13-reports": "Reports index",
    "14-report-ontime": "On-time performance report",
    "15-admin-airports": "Admin: airports with their timing rules (generic CRUD)",
    "16-admin-airport-edit": "Admin: editing an airport's curfew, slots, connection and turnaround times",
    "17-schema": "Schema browser: tables with exact row counts, and views",
    "18-schema-rows": "Live row browser for a table (flight_delay)",
    "19-delay-impact": "Impact page after filing the 180-min delay: figures, notice, every knock-on change, missed connections",
    "20-cascade-trace": "Cascade trace: recursive tree of the delayed flight and passengers affected",
    "21-board-after-delay": "Delhi board after the delay: changed times highlighted",
    "22-mobile-dashboard": "Dashboard at phone width (390px)",
    "23-mobile-flights": "Flights at phone width: horizontally scrolling table",
}
shot_dir = os.path.join(ROOT, "docs", "screenshots")
present = sorted(f[:-4] for f in os.listdir(shot_dir) if f.endswith(".png")) if os.path.isdir(shot_dir) else []
v["SCREENSHOTS"] = md_table([{"File": f"`docs/screenshots/{n}.png`", "Shows": SHOTS.get(n, "")} for n in present]) \
    if present else "_(no screenshots captured)_"

ORDER = ["database/", "app.py", "src/", "tests/", "scripts/", "templates/", "static/", "requirements.txt",
         ".env.example", ".gitignore", "README.md", "docs/"]
files.sort(key=lambda p: (next((i for i, pre in enumerate(ORDER) if p.startswith(pre) or p == pre), 99), p))
src = []
for n, rel in enumerate(files, 1):
    ext = os.path.splitext(rel)[1] or os.path.basename(rel)
    lang = EXT_LANG.get(ext, "text")
    body = open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace").read().rstrip()
    src.append(f"### A.{n} `{rel}`\n\n````{lang}\n{body}\n````")
v["SOURCE"] = "\n\n".join(src)

# ---------------------------------------------------------------- 4. assemble
template = open(os.path.join(ROOT, "scripts", "report_template.md"), encoding="utf-8").read()
source = v.pop("SOURCE")
out = re.sub(r"\{\{([A-Z_]+)\}\}", lambda m: str(v[m.group(1)]) if m.group(1) in v else m.group(0), template)
missing = [p for p in re.findall(r"\{\{[A-Z_]+\}\}", out) if p != "{{SOURCE}}"]
assert not missing, missing
core = out.replace("{{SOURCE}}", "_The full source code is in `docs/REPORT_CONTEXT.md` (this core version leaves it out to stay small)._")
out = out.replace("{{SOURCE}}", source)  # last, so placeholders quoted inside the source are left alone
assert ENV["DB_PASSWORD"] not in out, "database password leaked into the report"
assert ENV["DB_PASSWORD"] not in core
open(OUT, "w", encoding="utf-8").write(out)
open(OUT.replace(".md", "_CORE.md"), "w", encoding="utf-8").write(core)
print(f"Wrote {os.path.relpath(OUT, ROOT)}: {len(out.splitlines()):,} lines, {len(out) // 1024} KB "
      f"(core version {len(core.splitlines()):,} lines, {len(core) // 1024} KB), "
      f"{len(files)} source files. Tests: " + "; ".join(r.split("**")[1] for r in results[1:]))
