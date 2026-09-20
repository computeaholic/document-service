.PHONY: help install test test-integration lint fmt format type typecheck check clean run up down migrate rollback

COMPOSE := docker compose
TEST_DATABASE_URL ?= postgresql+psycopg://test:test@localhost:5434/document_service_test

help:
	@echo "Available targets:"
	@echo "  install  - Install project with dev dependencies"
	@echo "  test     - Run tests with coverage enforcement against the dedicated test database"
	@echo "  test-integration - Run integration tests against the dedicated test database"
	@echo "  lint     - Run ruff"
	@echo "  fmt      - Run black"
	@echo "  format   - Alias for fmt"
	@echo "  typecheck - Run mypy"
	@echo "  type     - Alias for typecheck"
	@echo "  check    - Run lint + typecheck + test"
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
	@set -eu; \
	cleanup() { \
		$(COMPOSE) --profile test stop postgres-test >/dev/null 2>&1 || true; \
		$(COMPOSE) --profile test rm -fs postgres-test >/dev/null 2>&1 || true; \
	}; \
	trap cleanup EXIT INT TERM; \
	cleanup; \
	$(COMPOSE) --profile test up -d --wait postgres-test; \
	DATABASE_URL="$(TEST_DATABASE_URL)" alembic upgrade head; \
	TEST_DATABASE_URL="$(TEST_DATABASE_URL)" pytest --cov=src --cov-report=term-missing --cov-fail-under=95

test-integration:
	@set -eu; \
	cleanup() { \
		$(COMPOSE) --profile test stop postgres-test >/dev/null 2>&1 || true; \
		$(COMPOSE) --profile test rm -fs postgres-test >/dev/null 2>&1 || true; \
	}; \
	trap cleanup EXIT INT TERM; \
	cleanup; \
	$(COMPOSE) --profile test up -d --wait postgres-test; \
	DATABASE_URL="$(TEST_DATABASE_URL)" alembic upgrade head; \
	TEST_DATABASE_URL="$(TEST_DATABASE_URL)" pytest -m integration

lint:
	ruff check src

fmt:
	black src

format: fmt

typecheck:
	mypy src

type: typecheck

check: lint typecheck test

clean:
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .coverage

run:
	uvicorn api.app:app --reload --no-access-log

up:
	$(COMPOSE) up -d --wait api

down:
	$(COMPOSE) --profile test down --remove-orphans

migrate:
	alembic upgrade head

rollback:
	alembic downgrade -1
