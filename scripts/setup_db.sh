#!/usr/bin/env bash
# Builds the database from scratch: schema, seed data, triggers, procedures,
# views and a handful of sample delays.
#
#   bash scripts/setup_db.sh              # 7-day schedule (1,400 flights)
#   SEED_DAYS=28 bash scripts/setup_db.sh # 28-day schedule (5,600 flights)
#
# Connection settings come from the environment, falling back to .env.
set -euo pipefail
cd "$(dirname "$0")/.."

# .env fills in anything not already set in the environment
if [ -f .env ]; then
  while IFS='=' read -r key value || [ -n "$key" ]; do
    case "$key" in ''|\#*) continue ;; esac
    if [ -z "${!key:-}" ]; then export "$key=$value"; fi
  done < .env
fi

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-3306}"
DB_USER="${DB_USER:-root}"
DB_NAME="${DB_NAME:-airline_cascades}"
SEED_DAYS="${SEED_DAYS:-7}"
export MYSQL_PWD="${DB_PASSWORD:-}"

run() {
  mysql --protocol=TCP -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" "$@"
}

echo "==> Creating database $DB_NAME"
run -e "DROP DATABASE IF EXISTS \`$DB_NAME\`; CREATE DATABASE \`$DB_NAME\` CHARACTER SET utf8mb4;"

echo "==> Schema";              run "$DB_NAME" < database/01_schema.sql
echo "==> Reference data";      run "$DB_NAME" < database/02_seed_reference.sql
echo "==> Operational data ($SEED_DAYS days)"
{ echo "SET @seed_days = $SEED_DAYS;"; cat database/03_seed_operational.sql; } | run "$DB_NAME"
echo "==> Triggers";            run "$DB_NAME" < database/04_triggers.sql
echo "==> Procedures";          run "$DB_NAME" < database/05_procedures.sql
echo "==> Views";               run "$DB_NAME" < database/06_views.sql
echo "==> Sample delays";       run "$DB_NAME" < database/07_seed_delays.sql

run "$DB_NAME" -N -e "SELECT CONCAT('==> Done: ', (SELECT COUNT(*) FROM flight), ' flights, ',
  (SELECT COUNT(*) FROM passenger), ' passengers, ', (SELECT COUNT(*) FROM ticket), ' tickets')"
