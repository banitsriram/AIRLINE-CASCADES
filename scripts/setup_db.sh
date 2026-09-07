#!/bin/bash
set -e
cd "$(dirname "$0")/.."
source .env

echo "==> Creating database"
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" \
  -e "DROP DATABASE IF EXISTS $DB_NAME; CREATE DATABASE $DB_NAME CHARACTER SET utf8mb4;"

echo "==> Importing schema"
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < database/01_schema.sql

echo "==> Seeding reference data"
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < database/02_seed_reference.sql

echo "==> Seeding operational data"
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < database/03_seed_operational.sql

echo "==> Installing triggers"
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < database/04_triggers.sql

echo "==> Installing procedures"
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < database/05_procedures.sql

echo "==> Done"
