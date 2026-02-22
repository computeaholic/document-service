START_HERE — document-service

This repository follows the Project Spec Template discipline.

No implementation begins until specification is complete and frozen.

This document explains how to navigate and evaluate this repository.

1. Purpose of This Repository

document-service is a deliberately constrained backend service that demonstrates:

Explicit state modeling

Explicit failure modeling

Deterministic error handling

Transaction discipline

Optimistic concurrency control

Idempotent create semantics

Clean architectural boundaries

Mechanical CI enforcement

It is a bounded system.

It is not a platform, a framework, or a startup foundation.

2. Order of Execution (Binding)

No /src directory may exist until the following are complete:

SPEC_PACK.md completed in full.

CONSTRAINTS.md frozen.

CONVENTIONS.md adopted.

FAILURE_MODES.md completed.

TRADEOFFS.md completed.

INTERVIEW_DEFENSE.md drafted.

SYNC_LOCK.md committed.

FREEZE.md created and committed with commit hash.

Clarity precedes implementation.

3. Canonical Document Map (Authoritative)

The authoritative documentation spine is:

START_HERE.md
SPEC_PACK.md
CONSTRAINTS.md
CONVENTIONS.md
FAILURE_MODES.md
TRADEOFFS.md
INTERVIEW_DEFENSE.md
SYNC_LOCK.md
FREEZE.md
/docs/BACKEND_STACK_PROFILE.md

Important:

State model → SPEC_PACK.md §4

Testing strategy → SPEC_PACK.md §12

Operational considerations → SPEC_PACK.md §14

Specification artifacts may be grouped under /project_spec/ to reduce repository root clutter. START_HERE.md must remain at repository root.

4. Scope Guard

Scope is defined in:

SPEC_PACK.md §2

SYNC_LOCK.md

TRADEOFFS.md §2

Out-of-scope items are deliberate.

No feature expansion is permitted without:

Updating SPEC_PACK.md

Updating TRADEOFFS.md

Updating FREEZE.md

Recording new commit hash

No silent expansion.

5. Stack Profile

This repository inherits Backend Stack Profile v1.0.

See:

/docs/BACKEND_STACK_PROFILE.md

The following are frozen unless re-freeze occurs:

Python 3.12

FastAPI

Pydantic v2

SQLAlchemy 2.x

PostgreSQL

Alembic

pytest (80–85% coverage)

ruff / black / mypy

GitHub Actions

Docker + docker-compose

No silent dependency drift.

6. Structural Discipline

Required structure:

/src
  api/
  services/
  domain/
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

No dumping-ground folders.

No circular dependencies.

Dependency direction: api → services → domain.

Domain is framework-agnostic.

All mutations use explicit transaction boundaries.

See CONVENTIONS.md.

7. Failure Discipline

All failures are defined in:

FAILURE_MODES.md

Every failure includes:

Detection layer

HTTP response

Error code

Log level

Retry strategy

Idempotency behavior

If a failure is not documented, it is a design defect.

8. Freeze Protocol

Before implementation:

All spec documents must be complete.

FREEZE.md must contain:

Freeze date

Version

Commit hash

After freeze:

No new endpoints

No new entities

No dependency additions

No transaction model changes

No state model changes

Ambiguity discovered during implementation requires:

Stop → Update docs → Re-freeze.

9. Evaluation Criteria

This repository is evaluated on:

Determinism

Constraint discipline

Correct state enforcement

Concurrency safety

Idempotency correctness

Failure modeling completeness

Transaction atomicity

Operational clarity

Clean CI enforcement

Not on feature breadth.

10. How to Begin (After Freeze)

After FREEZE commit:

make up
make migrate
make run
make test

A clean clone must allow this without undocumented steps.

11. Boundary Reminder

This repository applies only to document-service.

No assumptions are imported from other repositories.

All decisions are local to this system.

No cross-repo coupling.

Clarity first.
Constraints first.
Then code.