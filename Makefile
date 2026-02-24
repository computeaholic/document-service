.PHONY: help install test lint format type check clean run up down migrate rollback

help:
	@echo "Available targets:"
	@echo "  install  - Install project with dev dependencies"
	@echo "  test     - Run tests with coverage enforcement"
	@echo "  lint     - Run ruff"
	@echo "  format   - Run black"
	@echo "  type     - Run mypy"
	@echo "  check    - Run lint + type + test"
	@echo "  clean    - Remove build artifacts"
	@echo "  run      - Run local development server"
	@echo "  up       - Start docker-compose services"
	@echo "  down     - Stop docker-compose services"
	@echo "  migrate  - Run database migrations (upgrade to head)"
	@echo "  rollback - Rollback last database migration"

install:
	pip install --upgrade pip
	pip install .[dev]

test:
	pytest --cov=src --cov-report=term-missing --cov-fail-under=80

lint:
	ruff check src

format:
	black src

type:
	mypy src

check: lint type test

clean:
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .coverage

run:
	uvicorn api.app:app --reload

up:
	docker-compose up -d

down:
	docker-compose down

migrate:
	alembic upgrade head

rollback:
	alembic downgrade -1
