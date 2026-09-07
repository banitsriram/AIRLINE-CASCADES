-- Run with: mysql -u root -p airline_cascades < setup.sql  (from inside database/)
SOURCE 01_schema.sql;
SOURCE 02_seed_reference.sql;
SOURCE 03_seed_operational.sql;
SOURCE 04_triggers.sql;
SOURCE 05_procedures.sql;
