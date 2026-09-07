from contextlib import contextmanager

from flask import flash
import mysql.connector


@contextmanager
def db_action(success_msg=None):
    """Runs a mutating service call, turning any DB error (FK violation,
    trigger SIGNAL, unique constraint) into a flashed message instead of a 500."""
    try:
        yield
        if success_msg:
            flash(success_msg, "success")
    except mysql.connector.Error as e:
        flash(f"Database error: {e.msg}", "error")
