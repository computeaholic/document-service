Backend Stack Profile v1.0 — Adopted by document-service

document-service formally adopts Backend Stack Profile v1.0 without modification.

No deviations are authorized at freeze time.

1. Language

Python 3.12

Enforcement:

Exact minor version pinned in pyproject.toml

Docker base image pinned (e.g., python:3.12.x-slim)

No floating major versions.

2. Framework

FastAPI

Usage constraints:

Explicit request/response models

No hidden dependency injection magic

No business logic in route handlers

3. Data Validation

Pydantic v2

Rules:

Request/response schemas explicitly defined

Validation errors mapped to validation_error

No silent coercion surprises

4. ORM

SQLAlchemy 2.x (Declarative only)

Rules enforced in document-service:

Explicit Session management

No global session objects

No legacy .query() style

All mutations inside:

with session.begin():
5. Database

PostgreSQL (Docker for local)

Rules enforced:

No SQLite

Explicit constraints:

PK on documents.id

Unique constraint on idempotency_keys.key

Enum or constrained string for status

Version column for optimistic concurrency

6. Migrations

Alembic

Enforced:

Initial schema migration required before implementation acceptance

Downgrade path required

CI must validate upgrade + downgrade

No manual schema changes.

7. Testing

pytest

Coverage:
80–85%

Enforced in document-service:

Domain transition tests

Illegal transition tests

Idempotency tests

Concurrency conflict test

Integration tests for API + DB

Migration smoke test

No skipped tests allowed in main branch.

8. Formatting & Linting

ruff

black

mypy

pre-commit

Enforced:

Pre-commit hooks required

CI blocks on lint/type/test failure

No direct pushes to main

9. CI

GitHub Actions

Pipeline must run:

Lint

Typecheck

Tests

Coverage threshold enforcement

Migration smoke test

No bypassing required checks.

10. Docker

Required artifacts:

Dockerfile (pinned base image)

docker-compose.yml (App + Postgres)

Make targets:

make up
make down
make fmt
make lint
make typecheck
make test
make migrate
make rollback
make run

Targets must work from clean checkout.

11. Error Envelope Contract

All error responses must follow:

{
  "error": {
    "code": "string_identifier",
    "message": "Human readable message"
  }
}

Enforced in document-service:

No raw stack traces

No default FastAPI error shapes

Domain errors mapped explicitly

409 used for version/idempotency conflicts

400 used for illegal transitions

12. Transaction Discipline

All database mutations must use:

with session.begin():

Enforced:

No implicit commits

No autocommit

No side effects outside transaction

Version increment inside same transaction

13. Idempotency Policy

Create operations must define:

Duplicate behavior

Constraint enforcement

Deterministic mapping of IntegrityError

Explicit idempotency key semantics

Enforced in document-service:

Idempotency-Key required on create

Same key + same payload → return original resource

Same key + different payload → 409

14. State Discipline

Since Document has state:

State transitions defined in domain layer

Illegal transitions raise domain exceptions

Illegal transitions tested explicitly

Terminal states immutable

No implicit state mutation.

15. Logging

Structured logging only

No print statements

No secret logging

Errors logged once at boundary

Log level aligned to FAILURE_MODES.md

16. Definition of Done (Stack-Level)

document-service is complete only if:

Spec Pack complete

Scope frozen

Constraints frozen

Failure matrix complete

State model complete

Migrations working (upgrade + downgrade)

Tests passing

CI green

No TODO placeholders

Documentation complete

Interview Defense doc written

Adoption Statement

document-service adopts Backend Stack Profile v1.0 without modification as of freeze date 2026-02-21.

Any deviation requires:

SPEC_PACK update

TRADEOFFS update

FREEZE.md revision

New commit hash

No silent variation allowed.