# Common tasks. Database settings come from the environment or .env.
.PHONY: install db db-month run test lint docker clean

install:        ## Install app and development dependencies
	pip install -r requirements-dev.txt

db:             ## Build the database with a 7-day schedule
	bash scripts/setup_db.sh

db-month:       ## Build the database with a 28-day schedule
	SEED_DAYS=28 bash scripts/setup_db.sh

run:            ## Serve on http://localhost:5000 with auto-reload
	FLASK_DEBUG=1 python app.py

test:           ## Run the test suite (rebuilds the database)
	pytest

lint:
	ruff check .

docker:         ## Build and start MySQL + the app in containers
	docker compose up --build

clean:
	rm -rf .pytest_cache .ruff_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
