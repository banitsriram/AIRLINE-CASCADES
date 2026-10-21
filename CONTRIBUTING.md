# Contributing

Bug reports, questions and pull requests are welcome.

## Setting up

You need Python 3.9+ and MySQL 8.0+ with the `mysql` client on your PATH.

```
cp .env.example .env     # point it at a MySQL user that can create databases
make install
make db
make run
```

Or `docker compose up --build` with nothing else installed.

## Making a change

- **SQL lives in two places only:** `database/*.sql` for schema, procedures,
  triggers and views, and `src/services/` for the queries the app runs.
  Routes and templates don't contain SQL.
- **Schema changes** go in `database/01_schema.sql` (and `00_drop_all.sql`
  for a new table). Update `docs/SCHEMA_DIAGRAM.md` and
  `docs/NORMALIZATION.md` to match.
- **Cascade rules** are in `compute_cascade_candidates()`. Any change there
  must keep the seeded schedule consistent at zero delay; `tests/test_cascade.py`
  checks that, and `docs/CASCADE_ENGINE.md` should explain the new behaviour.
- **Forms** must include `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`.

## Before opening a pull request

```
make lint
make test
```

The tests rebuild the database named in `.env` several times, so don't
point them at data you want to keep. CI runs the same checks on Python 3.9
and 3.13 against MySQL 8.0, and builds the Docker image.

Keep pull requests to one change, and say in the description what it
changes and how you checked it.
