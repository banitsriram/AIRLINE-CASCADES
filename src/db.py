from contextlib import contextmanager

import mysql.connector.pooling

from src.config import Settings

_pool = None


def init_pool():
    global _pool
    _pool = mysql.connector.pooling.MySQLConnectionPool(
        pool_name="airline_pool",
        pool_size=10,
        host=Settings.DB_HOST,
        port=Settings.DB_PORT,
        user=Settings.DB_USER,
        password=Settings.DB_PASSWORD,
        database=Settings.DB_NAME,
        autocommit=False,
    )


@contextmanager
def get_conn():
    global _pool
    if _pool is None:
        init_pool()
    conn = _pool.get_connection()
    try:
        yield conn
    finally:
        conn.close()


def query(sql, params=None):
    with get_conn() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params or ())
        rows = cursor.fetchall()
        cursor.close()
        return rows


def execute(sql, params=None):
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params or ())
        conn.commit()
        lastrowid = cursor.lastrowid
        cursor.close()
        return lastrowid


def call_proc(proc_name, args=None):
    """Call a stored procedure and return all result sets (list of list-of-dict)."""
    with get_conn() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.callproc(proc_name, args or ())
        result_sets = []
        for result in cursor.stored_results():
            result_sets.append(result.fetchall())
        cursor.close()
        conn.commit()
        return result_sets
