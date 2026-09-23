"""Table-driven CRUD for the reference/lookup entities. Table and column names
below are hardcoded config, never user input, so the f-string SQL is safe."""

from src.db import query, execute

ENTITIES = {
    "airport": {
        "table": "airport",
        "pk": "airport_id",
        "label": "Airports",
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


def _columns(cfg):
    return ", ".join([cfg["pk"]] + [f["name"] for f in cfg["fields"]])


def _values(cfg, data):
    values = []
    for f in cfg["fields"]:
        v = data.get(f["name"]) or None
        if v and f["type"] == "datetime":
            v = v.replace("T", " ")
        values.append(v)
    return values


def list_rows(entity):
    cfg = ENTITIES[entity]
    return query(f"SELECT {_columns(cfg)} FROM {cfg['table']} ORDER BY {cfg['order_by']}")


def get_row(entity, row_id):
    cfg = ENTITIES[entity]
    rows = query(f"SELECT {_columns(cfg)} FROM {cfg['table']} WHERE {cfg['pk']}=%s", (row_id,))
    return rows[0] if rows else None


def create_row(entity, data):
    cfg = ENTITIES[entity]
    names = [f["name"] for f in cfg["fields"]]
    placeholders = ", ".join(["%s"] * len(names))
    return execute(
        f"INSERT INTO {cfg['table']} ({', '.join(names)}) VALUES ({placeholders})",
        _values(cfg, data),
    )


def update_row(entity, row_id, data):
    cfg = ENTITIES[entity]
    names = [f["name"] for f in cfg["fields"]]
    set_clause = ", ".join([f"{n}=%s" for n in names])
    execute(
        f"UPDATE {cfg['table']} SET {set_clause} WHERE {cfg['pk']}=%s",
        _values(cfg, data) + [row_id],
    )


def delete_row(entity, row_id):
    cfg = ENTITIES[entity]
    execute(f"DELETE FROM {cfg['table']} WHERE {cfg['pk']}=%s", (row_id,))
