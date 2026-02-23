Create the file:

.github/copilot-instructions.md

Content:

# Copilot Execution Contract — document-service

This repository is a spec-first, freeze-locked backend artifact.

Copilot must operate under strict constraints.

## 1. Architectural Boundaries

All authoritative system definitions live under:

/project_spec/

Copilot may NOT:

- Expand scope beyond SPEC_PACK.md
- Introduce new dependencies
- Modify state transitions
- Modify transaction boundaries
- Introduce background processes
- Introduce caching
- Add authentication
- Add pagination or list endpoints
- Add new entities
- Introduce convenience abstractions
- Introduce implicit transaction behavior
- Modify error envelope structure

If ambiguity exists:
Stop.
Request spec clarification.

## 2. Implementation Order

Implementation must follow this sequence:

1. Domain layer (pure Python, no framework)
2. Domain unit tests
3. Persistence layer (SQLAlchemy)
4. Repository layer
5. Service layer (explicit transaction boundaries)
6. API layer (FastAPI)
7. Integration tests

No framework code in domain layer.

No DB session usage outside service layer.

All mutations must use:

with session.begin():

## 3. Error Discipline

All errors must map to the deterministic error envelope:

{
  "error": {
    "code": "machine_readable_identifier",
    "message": "human readable explanation"
  }
}

No raw exceptions may leak.

No stack traces returned.

## 4. Concurrency Discipline

All mutation endpoints require If-Match header.

Optimistic concurrency must:

- Compare expected version
- Return 409 version_conflict on mismatch
- Increment version exactly by 1 on success

## 5. Idempotency Discipline

POST /documents must require Idempotency-Key header.

Behavior:

- Same key + same payload → return original document
- Same key + different payload → 409 idempotency_key_conflict

Idempotency must use a persistence table.

No in-memory idempotency allowed.

## 6. Structural Rules

File layout must follow:

/src
    /domain
    /services
    /infra
    /api

No "utils" folder.
No circular imports.
Dependency direction: api → services → domain.

## 7. Testing Discipline

Every failure matrix row must have at least one test.

Every illegal state transition must be tested.

Coverage target: 80–85%.

No placeholder tests.

## 8. Freeze Respect

SPEC_PACK.md and FREEZE.md are binding.

If implementation contradicts spec:
Stop.
Do not proceed.

Copilot is an assistant, not an architect.

The engineer retains architectural authority.