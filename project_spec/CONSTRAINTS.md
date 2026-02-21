Constraints — document-service

This document defines the non-negotiable constraints for document-service.

Constraints exist to prevent drift, reduce ambiguity, and enforce consistency.

They are binding once FREEZE.md is date stamped.

1. Stack Freeze

The following stack is frozen for this project.

Language:
Python 3.12 (exact minor pinned in .python-version or pyproject.toml)

Framework:
FastAPI

Database:
PostgreSQL (Docker-based local runtime)

Migration Tool:
Alembic

ORM:
SQLAlchemy 2.x (declarative, no legacy patterns)

Validation:
Pydantic v2

Testing Tools:
pytest + pytest-cov

Formatting Tools:
black

Linting Tools:
ruff + mypy

CI Provider:
GitHub Actions

Containerization Strategy:
Dockerfile with pinned Python base image (no latest)
docker-compose for local Postgres only

Stack Change Policy

Changes require:

Clear justification in TRADEOFFS.md

Alternatives considered

Impact assessment (complexity, LOC, surface area)

SPEC PACK update

FREEZE.md revision

No silent stack changes.

No tool swapping during implementation phase.

2. Dependency Rules
General Rules

No dependency added without written justification.

No dependency added for convenience alone.

No dependency added without production relevance.

No experimental or trend-driven libraries.

No dependency that expands scope implicitly.

This repo intentionally avoids:

ORMs beyond SQLAlchemy

Async task queues

Retry frameworks

API wrapper libraries

Event libraries

Caching libraries

Observability frameworks beyond structured logging

Required Documentation for New Dependency

If a dependency is proposed, it must document:

Why it is required

What alternative was rejected

What complexity it introduces

Why it does not expand scope

Estimated LOC impact

If justification cannot survive an interview defense, the dependency is rejected.

3. Structural Rules
3.1 Dependency Direction

Dependency flow must be one-directional:

api → services → domain
infrastructure → services (injected)
domain must not import infrastructure

Strict rules:

Domain layer contains pure business rules only.

Domain has zero FastAPI imports.

Domain has zero SQLAlchemy imports.

No circular imports.

No upward imports.

No cross-layer reach-through.

Violations require immediate correction.

3.2 Layer Isolation

Domain logic must remain framework-agnostic.

Infrastructure (DB models, session handling) must not contain business rules.

API layer must not contain domain logic.

Services coordinate transactions and orchestration.

Services do not own invariants — domain does.

If domain rules appear in API handlers, it is a defect.

3.3 Folder Discipline

The structure must reflect architecture.

Allowed high-level layout (after SPEC completion):

src/
  api/
  services/
  domain/
  infrastructure/

Rules:

No utils dumping ground.

No common catch-all folders.

No ambiguous folder names.

No helper modules with unclear ownership.

Every folder must map to architectural responsibility.

If a file cannot clearly belong to a layer, architecture is wrong.

3.4 Naming Conventions

snake_case for files and modules

PascalCase for classes

UPPER_SNAKE for constants

Explicit, descriptive identifiers

No cryptic abbreviations

No implicit semantics

Examples:

Good:

document_service.py

version_conflict_error.py

document_transition.py

Bad:

helpers.py

misc.py

doc.py

svc.py

Consistency is required across the entire project.

4. Transaction Discipline

All mutations must define explicit transaction boundaries.

with session.begin(): required for mutation endpoints.

No implicit commits.

No hidden writes.

No multi-step writes outside atomic context.

Version increment must occur within the same transaction as mutation.

Idempotency key write must be part of the same transaction as document creation.

If a write occurs outside explicit transaction scope, it is a defect.

5. Error Handling Discipline

All errors must follow the defined error envelope.

No raw exceptions may escape to the client.

No default FastAPI exception responses.

No silent failures.

No inconsistent error formats.

All domain exceptions must map deterministically to HTTP status + error code.

Each failure must log exactly once.

If an exception handler returns different shapes across endpoints, it is a defect.

6. Documentation Discipline

Documentation must be concise and structured.

No marketing language.

No vague phrases like “scalable” or “enterprise-grade.”

No speculative future extensibility sections.

No TODO placeholders.

No “phase 2” statements.

No comments that contradict SPEC PACK.

All documentation must reflect implemented behavior.

7. Scope Discipline

Scope is frozen after FREEZE.md is stamped.

Any expansion requires:

SPEC PACK update

FREEZE.md revision

TRADEOFFS.md entry

No feature creep.

No implicit enhancements during implementation.

No adding “small extras” because it feels easy.

If a change introduces:

A new endpoint

A new entity

A new background process

A new dependency

It requires spec revision first.

8. Concurrency Discipline

Optimistic locking via integer version is mandatory.

If-Match header required on all mutation endpoints except create.

409 returned on version mismatch.

No server-side retries.

No hidden auto-merge logic.

First writer wins.

Client refresh required.

Concurrency behavior must be deterministic and test-backed.

9. Testing Discipline

Every illegal transition must have a test.

Every failure matrix row must have a test.

Concurrency conflict must have an integration test.

Migration upgrade + downgrade must run in CI.

Coverage must remain between 80–85%.

Tests must assert error envelope structure.

No mocking core domain logic.

No skipping tests.

No commented-out tests.

Tests derive from SPEC PACK — not from implementation convenience.

10. Operational Discipline

No hidden configuration.

All required environment variables documented.

Health and readiness endpoints required.

Dockerfile must pin base image version.

No latest tags.

No mutable build arguments without documentation.

No environment-based branching logic beyond documented flags.

11. Ego Discipline

This repo exists to signal:

Deterministic thinking

Failure-first design

Transactional discipline

Concurrency awareness

Constraint control

Operational maturity

It does not exist to:

Demonstrate cleverness

Add architectural flourishes

Showcase trend technologies

Over-engineer abstractions

Build a platform

If something is not necessary for the SPEC PACK, it is not included.

Constraints are binding.

Violation requires correction before further implementation.

No drift.
No silent expansion.
No velocity trap.