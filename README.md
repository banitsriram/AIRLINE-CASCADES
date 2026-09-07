# Airline Cascades — DBMS CIA 3 Project

Airline flight-delay cascade simulator. When one flight is delayed, downstream
flights sharing the same aircraft get delayed too — modeled with a
self-referencing foreign key on `flight` and traversed with a recursive CTE.

15-table schema (3NF, two documented denormalizations), 6 triggers, 3 stored
procedures, full CRUD across 8 major entities.

## Prerequisites

- Python 3.9+
- MySQL 8.0+ running locally (needed for `WITH RECURSIVE` and `CHECK` constraint enforcement)
- pip

## Setup (three commands)

```
cp .env.example .env      # then edit .env with your MySQL password
pip install -r requirements.txt
bash scripts/setup_db.sh
```

## Run

```
python app.py
```

Open http://localhost:5000

## Docs

- `docs/CRUD_MATRIX.md` — which UI page implements each CRUD cell
- `docs/NORMALIZATION.md` — per-table 3NF justification
- `docs/VIVA_PREP.md` — Q&A for oral defence
- `docs/SCHEMA_DIAGRAM.md` — relationship description
- `docs/DEVIATIONS.md` — spec deviations
# AIRLINE-CASCADES
