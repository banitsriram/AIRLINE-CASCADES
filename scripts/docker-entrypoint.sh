#!/usr/bin/env bash
# Waits for MySQL, builds the database on first start, then serves the app.
set -euo pipefail
cd "$(dirname "$0")/.."

python - <<'PY'
import time
import mysql.connector
from src.config import Settings

for attempt in range(60):
    try:
        mysql.connector.connect(host=Settings.DB_HOST, port=Settings.DB_PORT, user=Settings.DB_USER,
                                password=Settings.DB_PASSWORD).close()
        break
    except mysql.connector.Error as e:
        print(f"waiting for MySQL at {Settings.DB_HOST}:{Settings.DB_PORT} ({e.msg})", flush=True)
        time.sleep(2)
else:
    raise SystemExit("MySQL never came up")
PY

built=$(python -c "
from src.config import Settings
import mysql.connector
c = mysql.connector.connect(host=Settings.DB_HOST, port=Settings.DB_PORT, user=Settings.DB_USER, password=Settings.DB_PASSWORD)
cur = c.cursor()
cur.execute('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s AND table_name = %s', (Settings.DB_NAME, 'flight'))
print(cur.fetchone()[0])
")

if [ "$built" = "0" ] || [ "${REBUILD_DB:-0}" = "1" ]; then
  bash scripts/setup_db.sh
fi

exec gunicorn --workers "${WEB_WORKERS:-3}" --bind "0.0.0.0:${PORT:-5000}" --access-logfile - app:app
