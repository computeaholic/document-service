SYNC LOCK — document-service

This document captures the authoritative mission and architectural boundaries of this repository.

It mirrors the original ultra-dense sync message used to initialize the project.

It exists to prevent context drift.

It is binding.

This file applies only to document-service.
No assumptions are imported from other repositories.

1. Project Identity

Repository Name:
document-service

Primary Objective:
Build a constrained, production-realistic backend service that demonstrates explicit state control, transaction discipline, optimistic concurrency, idempotent creation, and deterministic failure handling.

This repository is intentionally bounded.

It is NOT:

A platform

A startup foundation

A distributed system

A feature playground

A demo scaffold

A technology showcase

It exists to demonstrate senior-level engineering discipline.

2. Core Demonstrations (Non-Negotiable)

This repository must clearly demonstrate:

Explicit state modeling (document approval workflow)

Explicit failure modeling (complete failure matrix)

Deterministic error handling (stable error envelope + codes)

Transaction discipline (with session.begin():)

Concurrency discipline (optimistic locking via integer version)

Idempotency (create operation via Idempotency-Key)

Clean architectural boundaries (api → services → domain)

Mechanical CI enforcement (lint + type + test gates)

Operational clarity (health/readiness endpoints, migrations)

These demonstrations define success.

They may not be removed without:

Updating SPEC_PACK.md

Updating TRADEOFFS.md

Updating FREEZE.md

Recording a new commit hash

3. Stack Lock

This repository inherits Backend Stack Profile v1.0.

The following are frozen unless formally revised:

Python 3.12

FastAPI

Pydantic v2

SQLAlchemy 2.x (declarative style only)

PostgreSQL

Alembic

pytest (80–85% coverage)

ruff

black

mypy

GitHub Actions

Docker + docker-compose

Stack changes require:

Update to CONSTRAINTS.md

Update to TRADEOFFS.md

Update to SPEC_PACK.md

Freeze revision

No silent drift.

4. Scope Guard

The scope defined in SPEC_PACK.md is binding.

The system includes:

Single business entity: Document

Single workflow: draft → submitted → approved/rejected

6 domain endpoints + health endpoints

Explicit idempotent create

Explicit optimistic concurrency

No background jobs

Out-of-scope items are intentional:

Authentication

Authorization

Audit logs

Background processing

Caching

Pagination

Search

Distributed scaling

No features may be added without:

Updating SPEC_PACK.md

Updating TRADEOFFS.md

Updating FREEZE.md

Recording a new commit hash

No implicit expansion.
No “just this one improvement.”

5. Complexity Budget

The complexity budget defined in SPEC_PACK.md is binding.

Budget includes:

Max endpoints: 9

Max domain entities: 1 business entity (+ idempotency table)

Max background processes: 0

Maximum abstraction layers: 3 (api → services → domain)

Target LOC: ~2.5k–3.2k

Exceeding the budget requires formal revision and re-freeze.

Constraint precedes ambition.

6. Implementation Discipline

No implementation in /src may contradict:

State model

Failure matrix

Transaction model

Concurrency model

Error envelope contract

Idempotency policy

Stack constraints

Dependency direction rules

If implementation reveals ambiguity:

Stop.
Update SPEC_PACK.md.
Revise documentation.
Re-freeze.

Velocity does not override correctness.

7. Enforcement

This document functions as a boundary contract.

All engineering decisions must remain consistent with this file.

If drift occurs:

Pause development

Correct documentation

Re-freeze before continuing

This repository is judged on:

Clarity

Correctness

Constraint discipline

Determinism

Failure awareness

Transactional maturity

Not on cleverness.