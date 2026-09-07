from src.db import query
from src.config import Settings


def tables():
    return query(
        """SELECT table_name AS table_name, table_rows AS table_rows, create_time AS create_time
           FROM information_schema.tables
           WHERE table_schema = %s AND table_type = 'BASE TABLE'
           ORDER BY table_name""",
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
