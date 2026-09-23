"""Table-driven CRUD for the reference/lookup entities. Table and column names
below are hardcoded config, never user input, so the f-string SQL is safe."""

from src.db import query, execute
from src.services.lookups import enum_values

ENTITIES = {
    "airport": {
        "table": "airport",
        "pk": "airport_id",
        "label": "Airports",
        "item": "airport",
        "order_by": "iata_code",
        "fields": [
            {"name": "iata_code", "type": "text", "required": True, "label": "IATA"},
            {"name": "icao_code", "type": "text", "required": False, "label": "ICAO"},
            {"name": "city", "type": "text", "required": True, "label": "City"},
            {"name": "country", "type": "text", "required": True, "label": "Country"},
            {"name": "timezone", "type": "text", "required": True, "label": "Timezone"},
            {"name": "open_time", "type": "time", "required": False, "label": "Opens (curfew)"},
            {"name": "close_time", "type": "time", "required": False, "label": "Closes (curfew)"},
            {"name": "runway_slots_per_hour", "type": "number", "required": True, "label": "Departures / hour"},
            {"name": "min_connect_min", "type": "number", "required": True, "label": "Min connection (min)"},
            {"name": "min_turnaround_min", "type": "number", "required": True, "label": "Min turnaround (min)"},
        ],
    },
    "gate": {
        "table": "gate",
        "pk": "gate_id",
        "label": "Gates",
        "item": "gate",
        "order_by": "airport_id, terminal, gate_id",
        "fields": [
            {"name": "airport_id", "type": "fk", "required": True, "label": "Airport", "ref": "airport"},
            {"name": "gate_code", "type": "text", "required": True, "label": "Gate"},
            {"name": "terminal", "type": "text", "required": True, "label": "Terminal"},
        ],
    },
    "aircraft_type": {
        "table": "aircraft_type",
        "pk": "type_id",
        "label": "Aircraft Types",
        "item": "aircraft type",
        "order_by": "manufacturer, model",
        "fields": [
            {"name": "model", "type": "text", "required": True, "label": "Model"},
            {"name": "manufacturer", "type": "text", "required": True, "label": "Manufacturer"},
            {"name": "seat_capacity", "type": "number", "required": True, "label": "Seat Capacity"},
            {"name": "max_range_km", "type": "number", "required": True, "label": "Max Range (km)"},
            {"name": "cruise_speed_kmh", "type": "number", "required": False, "label": "Cruise Speed (km/h)"},
        ],
    },
    "delay_reason": {
        "table": "delay_reason",
        "pk": "reason_id",
        "label": "Delay Reasons",
        "item": "delay reason",
        "order_by": "category",
        "fields": [
            {
                "name": "category",
                "type": "select",
                "required": True,
                "label": "Category",
                "options": ["WEATHER", "ATC", "TECHNICAL", "CREW", "SECURITY", "FUEL", "MAINTENANCE", "CASCADE"],
            },
            {"name": "description", "type": "text", "required": True, "label": "Description"},
        ],
    },
    "delay_code": {
        "table": "delay_code",
        "pk": "code_id",
        "label": "IATA Delay Codes",
        "item": "IATA delay code",
        "order_by": "iata_code",
        "fields": [
            {"name": "iata_code", "type": "text", "required": True, "label": "Code"},
            {"name": "description", "type": "text", "required": True, "label": "Description"},
            {"name": "reason_id", "type": "fk", "required": True, "label": "Category", "ref": "delay_reason"},
        ],
    },
    "route": {
        "table": "route",
        "pk": "route_id",
        "label": "Routes",
        "item": "route",
        "order_by": "route_id",
        "fields": [
            {"name": "origin_airport_id", "type": "fk", "required": True, "label": "Origin", "ref": "airport"},
            {"name": "dest_airport_id", "type": "fk", "required": True, "label": "Destination", "ref": "airport"},
            {"name": "distance_km", "type": "number", "required": True, "label": "Distance (km)"},
            {"name": "std_duration_min", "type": "number", "required": True, "label": "Duration (min)"},
        ],
    },
    "aircraft": {
        "table": "aircraft",
        "pk": "aircraft_id",
        "label": "Aircraft",
        "item": "aircraft",
        "order_by": "registration",
        "fields": [
            {"name": "registration", "type": "text", "required": True, "label": "Registration"},
            {"name": "type_id", "type": "fk", "required": True, "label": "Type", "ref": "aircraft_type"},
            {"name": "base_airport_id", "type": "fk", "required": True, "label": "Base Airport", "ref": "airport"},
            {
                "name": "status",
                "type": "select",
                "required": True,
                "label": "Status",
                "options": ["ACTIVE", "MAINTENANCE", "GROUNDED", "RETIRED"],
            },
        ],
    },
    "maintenance_log": {
        "table": "maintenance_log",
        "pk": "maint_id",
        "label": "Maintenance Log",
        "item": "maintenance entry",
        "order_by": "maint_start DESC",
        "fields": [
            {"name": "aircraft_id", "type": "fk", "required": True, "label": "Aircraft", "ref": "aircraft"},
            {"name": "maint_start", "type": "datetime", "required": True, "label": "Start"},
            {"name": "maint_end", "type": "datetime", "required": True, "label": "End"},
            {
                "name": "type",
                "type": "select",
                "required": True,
                "label": "Type",
                "options": [
                    "SCHEDULED", "UNSCHEDULED", "A_CHECK", "B_CHECK", "C_CHECK", "D_CHECK", "LINE_MAINTENANCE",
                ],
            },
        ],
    },
}

REF_LOOKUPS = {
    "airport": ("airport", "airport_id", "iata_code"),
    "aircraft_type": ("aircraft_type", "type_id", "model"),
    "aircraft": ("aircraft", "aircraft_id", "registration"),
    "delay_reason": ("delay_reason", "reason_id", "category"),
}


def fk_options(ref):
    table, pk, label_col = REF_LOOKUPS[ref]
    return query(f"SELECT {pk} AS id, {label_col} AS label FROM {table} ORDER BY {label_col}")


# MySQL data types -> form field types, for columns added after this config was written.
_INPUT_TYPES = {
    "int": "number", "bigint": "number", "smallint": "number", "tinyint": "number", "mediumint": "number",
    "decimal": "number", "float": "number", "double": "number",
    "date": "date", "datetime": "datetime", "timestamp": "datetime", "time": "time", "enum": "select",
}


def _q(name):
    """Backtick-quote an identifier (names come from config or information_schema)."""
    return "`" + name.replace("`", "``") + "`"


def fields(entity):
    """The configured fields that still exist, plus any column added to the table
    since (ALTER TABLE ... ADD COLUMN), read live from information_schema.
    ENUM options are read live too, so ALTER ... MODIFY ENUM shows up at once."""
    cfg = ENTITIES[entity]
    live = {
        c["name"]: c
        for c in query(
            """SELECT column_name AS name, data_type AS dtype, column_type AS ctype,
                      is_nullable AS nullable, column_default AS dflt, extra AS extra
               FROM information_schema.columns
               WHERE table_schema = DATABASE() AND table_name = %s
               ORDER BY ordinal_position""",
            (cfg["table"],),
        )
    }
    out = []
    for f in cfg["fields"]:
        if f["name"] not in live:
            continue  # column was dropped
        f = dict(f)
        if f["type"] == "select":
            f["options"] = enum_values(cfg["table"], f["name"]) or f["options"]
        out.append(f)

    known = {f["name"] for f in cfg["fields"]} | {cfg["pk"], "created_at", "updated_at"}
    for name, c in live.items():
        generated = "GENERATED" in c["extra"].upper() and "DEFAULT_GENERATED" not in c["extra"].upper()
        if name in known or generated:
            continue
        ftype = _INPUT_TYPES.get(c["dtype"].lower(), "text")
        out.append({
            "name": name,
            "type": ftype,
            "required": c["nullable"] == "NO" and c["dflt"] is None and "auto_increment" not in c["extra"],
            "label": name.replace("_", " ").capitalize(),
            "options": enum_values(cfg["table"], name) if ftype == "select" else None,
            "added": True,
        })
    return out


def _values(flds, data):
    values = []
    for f in flds:
        v = data.get(f["name"]) or None
        if v and f["type"] == "datetime":
            v = v.replace("T", " ")
        values.append(v)
    return values


def _select(cfg, flds):
    return ", ".join(_q(n) for n in [cfg["pk"]] + [f["name"] for f in flds])


def list_rows(entity, flds):
    cfg = ENTITIES[entity]
    return query(f"SELECT {_select(cfg, flds)} FROM {_q(cfg['table'])} ORDER BY {cfg['order_by']}")


def get_row(entity, row_id, flds):
    cfg = ENTITIES[entity]
    rows = query(f"SELECT {_select(cfg, flds)} FROM {_q(cfg['table'])} WHERE {_q(cfg['pk'])}=%s", (row_id,))
    return rows[0] if rows else None


def create_row(entity, data, flds):
    cfg = ENTITIES[entity]
    placeholders = ", ".join(["%s"] * len(flds))
    return execute(
        f"INSERT INTO {_q(cfg['table'])} ({', '.join(_q(f['name']) for f in flds)}) VALUES ({placeholders})",
        _values(flds, data),
    )


def update_row(entity, row_id, data, flds):
    cfg = ENTITIES[entity]
    set_clause = ", ".join(f"{_q(f['name'])}=%s" for f in flds)
    execute(
        f"UPDATE {_q(cfg['table'])} SET {set_clause} WHERE {_q(cfg['pk'])}=%s",
        _values(flds, data) + [row_id],
    )


def delete_row(entity, row_id):
    cfg = ENTITIES[entity]
    execute(f"DELETE FROM {cfg['table']} WHERE {cfg['pk']}=%s", (row_id,))
