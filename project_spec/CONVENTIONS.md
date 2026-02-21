Conventions — document-service

This document defines project conventions for document-service.

Conventions exist to enforce predictability, reduce review overhead, and ensure all three portfolio repositories are structurally identical.

They are binding once FREEZE.md is stamped.

1. Repository Structure

document-service must use the following structure:

/
  START_HERE.md
  README.md
  sync message.txt
  SPEC_PACK.md
  CONSTRAINTS.md
  CONVENTIONS.md
  FAILURE_MODES.md
  TRADEOFFS.md
  FREEZE.md
  PROJECT_INIT_CHECKLIST.md
  /docs
  /src
    api/
    domain/
    services/
    infrastructure/
    config/
    main.py
  /tests
  Makefile
  pyproject.toml
  Dockerfile
  docker-compose.yml
  .pre-commit-config.yaml
  .github/workflows/ci.yml

Rules:

No extra top-level folders without documented justification.

No unused folders.

No “misc”, “common”, or dumping-ground directories.

Maximum abstraction layers: 3 (api → services → domain).

infrastructure is an implementation detail layer, not a business layer.

config may contain settings and environment handling only.

If a folder cannot clearly justify its existence, it must not exist.

2. Dependency Direction

Allowed direction:

api → services → domain

infrastructure → services (injected, not pulled upward)

config may be imported by api, services, infrastructure

domain must not import:

api

services

infrastructure

config

FastAPI

SQLAlchemy

Pydantic

Rules:

No upward imports.

No circular dependencies.

Domain must remain framework-agnostic and persistence-agnostic.

Services orchestrate but do not own invariants.

API layer maps HTTP ↔ service calls only.

Violation of dependency direction is a structural defect.

3. Naming Conventions

Files and modules:

snake_case

No camelCase filenames

No ambiguous abbreviations

Classes:

PascalCase

Constants:

UPPER_SNAKE_CASE

Identifiers:

Explicit, descriptive names

Avoid abbreviations unless universally understood (e.g., id)

Avoid single-letter variables outside small local scopes

Examples:

Good:

document_service.py

version_conflict_error.py

idempotency_repository.py

Bad:

helpers.py

misc.py

doc_svc.py

common_utils.py

Consistency across all three portfolio repos is required.

4. API Conventions

Error envelope (required everywhere):

{
  "error": {
    "code": "machine_identifier",
    "message": "human readable"
  }
}

Rules:

No raw exception details returned to clients.

Error codes are stable and documented in SPEC PACK.

All endpoints must document expected error codes.

Error mapping must occur at the API boundary layer only.

Services raise domain or application exceptions.

API layer maps exceptions → HTTP + envelope.

HTTP semantics must be consistent:

400 — illegal_transition

404 — not_found

409 — version_conflict / idempotency_key_conflict / db_conflict

422 — validation_error

503 — db_unavailable

504 — timeout

No endpoint returns inconsistent shapes.

5. Database and Migrations

Rules:

All schema changes require Alembic migrations.

Downgrade paths must exist.

CI must validate upgrade and downgrade.

No schema drift between SQLAlchemy models and database schema.

No manual schema edits.

Transaction discipline:

All mutations must use explicit transaction boundaries:

with session.begin():

No implicit commits.

No hidden writes.

No multi-step writes outside atomic context.

Version increment must occur in the same transaction as mutation.

Idempotency key write must be atomic with document creation.

6. Idempotency and Conflicts

Rules:

Create operations must define idempotency behavior.

POST /documents requires Idempotency-Key header.

Same key + same payload → return original document.

Same key + different payload → 409 idempotency_key_conflict.

Prefer DB constraints for dedupe/uniqueness.

IntegrityError must be mapped deterministically to 409 with stable code.

No implicit retry logic inside the service.

First writer wins.

7. Logging

Rules:

Structured logging only (JSON format).

No print statements.

No debug prints committed.

Do not log secrets.

Do not log full request bodies.

Errors are logged once at the API boundary.

Log entries must include:

request_id

route

status_code

error_code (if present)

relevant identifiers (e.g., document_id)

No duplicate logs for the same failure.

8. Testing

Requirements:

pytest is required.

Tests derive directly from:

Failure Matrix

State Model

Illegal state transitions must be tested.

Concurrency test required:

Two updates with same If-Match → one 409.

Idempotency behavior must be tested.

Coverage target: 80–85%.

Rules:

Avoid over-mocking core logic.

Prefer integration tests for API + DB behavior.

Tests must be deterministic.

No timing-based race assumptions.

No skipped tests.

No commented-out tests.

If a failure mode exists in SPEC PACK but has no test, it is incomplete.

9. Tooling and Quality Gates

Required tools:

ruff

black

mypy

pytest

pre-commit

GitHub Actions CI

Rules:

No direct push to main.

Pull Request required.

CI must pass (lint, typecheck, test) before merge.

Required checks may not be bypassed.

Pre-commit hooks must run locally.

No TODO stubs in finished project.

10. Makefile Targets

Each repo must provide consistent targets:

make fmt
make lint
make typecheck
make test
make test-cov
make up
make down
make run
make migrate
make rollback

Rules:

Targets must work from clean checkout.

Targets must not depend on undocumented setup.

Targets must be documented in README.

make up starts Postgres via docker-compose.

make run starts the API server.

make migrate applies Alembic upgrade.

make rollback applies downgrade.

Target names must match across all three repos.

11. Version Pinning

Rules:

Dependencies pinned in pyproject.toml.

No floating major versions.

Docker base image must not use latest.

CI versions must be explicit.

Tool versions must be stable and reproducible.

Reproducibility is required.

12. Stability Standard

This repository is a hiring artifact.

It must signal:

Deterministic structure

Clean boundaries

Controlled complexity

Explicit failure modeling

Operational realism

It must not signal:

Trend chasing

Premature abstraction

Clever indirection

Hidden magic

If something makes the code look “interesting” but not “disciplined,” it does not belong.

Conventions are binding.

If a convention must change:

Update SPEC PACK

Document in TRADEOFFS.md

Update FREEZE.md

Re-freeze

No drift.
No silent expansion.
No velocity trap.