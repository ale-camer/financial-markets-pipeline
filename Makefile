.PHONY: up down restart logs test lint shell db-airflow db-curated help

# Default target
help:
	@echo "Available commands:"
	@echo "  make up          - Start the containerized development environment"
	@echo "  make down        - Tear down containers and volumes"
	@echo "  make restart     - Restart the containers"
	@echo "  make logs        - Tail the docker compose logs"
	@echo "  make lint        - Run ruff linter inside the container"
	@echo "  make test        - Run unit tests inside the container"
	@echo "  make shell       - Open a bash session in the Airflow container"
	@echo "  make db-airflow  - Open psql for Airflow metadata DB"
	@echo "  make db-curated  - Open psql for Curated market data DB"

up:
	docker compose up -d --build

down:
	docker compose down -v

restart:
	docker compose down
	docker compose up -d

logs:
	docker compose logs -f

lint:
	docker compose run --rm airflow-webserver ruff check src/ dags/

test:
	docker compose run --rm airflow-webserver pytest tests/

shell:
	docker compose run --rm airflow-webserver bash

db-airflow:
	docker compose exec postgres psql -U airflow -d airflow

db-curated:
	docker compose exec postgres psql -U postgres -d market_data
