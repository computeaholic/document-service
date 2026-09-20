# START_HERE — document-service

For project overview, runtime behavior, and local usage, start with [README.md](README.md).

This document is for specification navigation, governance context, and repository structure.

## 1. Role of This Document

Use START_HERE.md to understand:

- where the design record lives
- how the specification documents relate to implementation
- which governance artifacts are still relevant when evaluating changes

Do not use this file as the primary product or usage overview.

## 2. Design Record Map

README remains the public front door for current overview, usage, architecture orientation, and operational entry.

Under `project_spec/`, the authority model is split intentionally:

- Frozen normative artifacts:
  - `project_spec/SPEC_PACK.md` — frozen behavioral contract and scope
  - `project_spec/FREEZE.md` — formal freeze record
  - `project_spec/SYNC_LOCK.md` — binding anti-drift boundary contract
  - `project_spec/BACKEND_STACK_PROFILE.md` — adopted backend stack baseline
- Living current governance and explanation:
  - `project_spec/CONSTRAINTS.md`
  - `project_spec/CONVENTIONS.md`
  - `project_spec/COPILOT.md`
  - `project_spec/FAILURE_MODES.md`
  - `project_spec/GITHUB_WORKFLOW.md`
  - `project_spec/INTERVIEW_DEFENSE.md`
  - `project_spec/TRADEOFFS.md`
- Process records:
  - `project_spec/PROJECT_INIT_CHECKLIST.md`
  - `sync message.txt`

Frozen does not mean obsolete. These artifacts remain authoritative for the boundaries they define.

## 3. How to Evaluate the Implementation

If you want to inspect the implementation directly, the shortest useful path is:

- `src/domain/document.py` — state machine and invariants
- `src/application/services.py` — use-case orchestration
- `src/infrastructure/postgres_repository.py` — persistence and database-level version guard
- `src/api/app.py` — HTTP contract, idempotency handling, readiness, and error mapping
- `src/tests/api/test_idempotency.py` and `src/tests/infrastructure/test_postgres_integration.py` — observable behavior under replay, versioning, and persistence

## 4. Governance Notes

This repository was built with a spec-first workflow.

- implementation is expected to stay inside the frozen scope
- material changes to contract or architecture require design-record updates before code changes
- historical freeze records are kept as history, not continuously rewritten status summaries

## 5. Repository Boundaries

document-service is intentionally limited to a single document workflow and the correctness concerns around it.

It is not intended as:

- a general workflow engine
- a multi-entity platform
- a startup scaffold
- a background-processing system

The narrow scope is deliberate and documented in `project_spec/TRADEOFFS.md`.