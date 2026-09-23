from src.db import query
from src.config import Settings


def _q(name):
    return "`" + name.replace("`", "``") + "`"


def tables():
    """Base tables with EXACT row counts. information_schema.tables.table_rows is
    an InnoDB estimate that MySQL caches (information_schema_stats_expiry), so it
    goes stale right after someone inserts rows by hand."""
    rows = query(
        """SELECT table_name AS table_name, create_time AS create_time
           FROM information_schema.tables
           WHERE table_schema = %s AND table_type = 'BASE TABLE'
           ORDER BY table_name""",
        (Settings.DB_NAME,),
    )
    for r in rows:
        r["table_rows"] = query(f"SELECT COUNT(*) AS n FROM {_q(r['table_name'])}")[0]["n"]
    return rows


def views():
    return query(
        """SELECT table_name AS table_name FROM information_schema.views
           WHERE table_schema = %s ORDER BY table_name""",
        (Settings.DB_NAME,),
    )


def columns(table_name):
    return query(
        """SELECT column_name AS column_name, column_type AS column_type,
                  is_nullable AS is_nullable, column_key AS column_key,
                  column_default AS column_default, extra AS extra
           FROM information_schema.columns
           WHERE table_schema = %s AND table_name = %s
           ORDER BY ordinal_position""",
        (Settings.DB_NAME, table_name),
    )


def foreign_keys(table_name):
    return query(
        """SELECT column_name AS column_name,
                  referenced_table_name AS referenced_table_name,
                  referenced_column_name AS referenced_column_name
           FROM information_schema.key_column_usage
           WHERE table_schema = %s AND table_name = %s AND referenced_table_name IS NOT NULL""",
        (Settings.DB_NAME, table_name),
    )


def record(table, pk, row_id):
    """Every column of one row, exactly as stored. Table and key names are
    hard-coded by the calling route, never user input."""
    rows = query(f"SELECT * FROM {_q(table)} WHERE {_q(pk)} = %s", (row_id,))
    return rows[0] if rows else None


def rows_page(table, page, per_page=50):
    """One page of SELECT * from a table or view, with its live column list.
    The name has already been checked against information_schema by the route."""
    total = query(f"SELECT COUNT(*) AS n FROM {_q(table)}")[0]["n"]
    rows = query(f"SELECT * FROM {_q(table)} LIMIT %s OFFSET %s", (per_page, (page - 1) * per_page))
    cols = [c["column_name"] for c in columns(table)]
    return cols, rows, total
