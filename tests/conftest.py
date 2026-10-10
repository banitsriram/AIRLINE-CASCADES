"""Every test module starts from a freshly built database (scripts/setup_db.sh),
since filing delays, running the clock and the live-change checks all write to
it. Connection settings come from the environment or .env, as for the app.

    pytest            # needs MySQL 8 reachable with the settings in .env
"""
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app import app as flask_app  # noqa: E402
from src import db  # noqa: E402


def rebuild_database():
    subprocess.run(["bash", os.path.join(ROOT, "scripts", "setup_db.sh")], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # The old pool's connections were opened on the dropped database.
    db._pool = None


@pytest.fixture(scope="module")
def fresh_db():
    rebuild_database()
    yield


@pytest.fixture(scope="module")
def client(fresh_db):
    flask_app.config["TESTING"] = True
    return flask_app.test_client()
