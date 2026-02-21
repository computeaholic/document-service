SPEC PACK — document-service

No /src directory may be created until this document is complete and reviewed.

1. Mission
1.1 System Purpose

document-service is a small, finished backend HTTP service that stores and manages a single Document entity through a constrained approval workflow (draft → submitted → approved/rejected).

It solves the problem of safely mutating stateful business objects with explicit rules, atomic transactions, idempotent creation, and optimistic concurrency so clients can interact predictably even under retries and concurrent writes.

The primary user is another service or a simple internal client that needs to create and progress documents through approval with clear failure behavior.

The invariant that must always hold:

A document’s state transitions and version updates are deterministic, rules-enforced, and atomic — no illegal transition or partial write can persist.

2. Scope Definition
2.1 In Scope

Create Document in draft state (idempotent via idempotency key)

Retrieve Document by id

Update Document while in draft (optimistic locking)

Submit Document (draft → submitted) with content non-empty invariant

Approve Document (submitted → approved)

Reject Document (submitted → rejected)

Deterministic error envelope + error code mapping

Health/readiness endpoints with DB connectivity check

Structured logging with log-once error policy

Alembic migrations (upgrade + downgrade)

CI enforcing lint/type/test + coverage gate

2.2 Out of Scope

Authentication / authorization / RBAC

Audit logging / immutable history

Notifications (email/webhooks)

Background jobs / queues / schedulers

Caching

Search

Pagination / list endpoints

Horizontal scaling / distributed coordination

Event sourcing / CQRS

External dependencies / third-party API calls

UI work

2.3 Non-Goals

Multi-entity workflows (no Users, Approvals, Comments, etc.)

“Flexible” workflow configuration (state machine is fixed)

High-throughput performance tuning

Multi-tenant support

Soft-delete, archival policies, or retention management

Partial update semantics (no PATCH)

Bulk operations

3. Domain Model
3.1 Entities
Entity	Purpose	Owner	Persistence	Notes
Document	Business object representing a document moving through a fixed approval workflow	Service	PostgreSQL (single table)	Uses optimistic version column; terminal states are immutable
3.2 Invariants

id is globally unique (UUID).

status ∈ {draft, submitted, approved, rejected}.

approved and rejected are terminal: no further mutations or transitions allowed.

A document cannot be approved or rejected unless it is currently submitted.

A document cannot be submitted unless content.strip().len > 0.

version is a non-negative integer and increments by exactly 1 on each successful mutation.

created_at is immutable after creation.

updated_at is set on each successful mutation.

Writes must be atomic: if any step fails, no partial persistence.

Enforcement:

Domain logic enforces transition rules and content non-empty on submit.

Database constraints enforce enum validity, not-null expectations, and unique constraints.

Optimistic concurrency enforced by comparing expected version to persisted version.

4. State Model
4.1 States

draft

submitted

approved (terminal)

rejected (terminal)

4.2 Legal Transitions
From State	To State	Condition	Enforced Where
draft	submitted	content.strip() non-empty	Domain logic
submitted	approved	none	Domain logic
submitted	rejected	none	Domain logic
4.3 Illegal Transitions

All illegal transitions return:

HTTP: 400

error.code: illegal_transition

Examples (explicitly tested):

approved → *

rejected → *

draft → approved

draft → rejected

submitted → draft

submitted → submitted

approved → approved

rejected → rejected

Error message must include current state and attempted action.

5. Interface / API Contract
5.1 Endpoints
Method	Path	Purpose	Idempotent?
POST	/documents	Create draft document	Yes
GET	/documents/{id}	Retrieve document	Yes
PUT	/documents/{id}	Update draft document	No
POST	/documents/{id}/submit	Draft → Submitted	No
POST	/documents/{id}/approve	Submitted → Approved	No
POST	/documents/{id}/reject	Submitted → Rejected	No
GET	/health/live	Liveness	Yes
GET	/health/ready	Readiness	Yes
5.2 Request Models
POST /documents

Headers:

Idempotency-Key (required): string (1–128 chars)

Body:

title (required): 1–200 chars (trimmed)

content (required): 0–20000 chars

Validation:

title must not be blank after trim

content max length enforced

PUT /documents/{id}

Headers:

If-Match (required): integer version

Body:

title (required)

content (required)

Rules:

Allowed only when status = draft

Version must match

POST /documents/{id}/submit

Headers:

If-Match (required)

Rules:

Status must be draft

Content must be non-empty

Version must match

POST /documents/{id}/approve

Headers:

If-Match (required)

Rules:

Status must be submitted

Version must match

POST /documents/{id}/reject

Headers:

If-Match (required)

Rules:

Status must be submitted

Version must match

5.3 Response Model
{
  "id": "uuid",
  "title": "string",
  "content": "string",
  "status": "draft|submitted|approved|rejected",
  "version": 0,
  "created_at": "iso8601",
  "updated_at": "iso8601"
}

POST returns 201.

5.4 Error Envelope Contract

All errors:

{
  "error": {
    "code": "machine_readable_identifier",
    "message": "human readable explanation"
  }
}

Frozen error codes:

validation_error (422)

not_found (404)

illegal_transition (400)

idempotency_key_conflict (409)

version_conflict (409)

db_conflict (409)

db_unavailable (503)

timeout (504)

internal_error (500)

6. Failure Matrix
Scenario	Detected At	HTTP	Log	Retry	Idempotent
Invalid input	Validation	422	INFO	No	N/A
Missing resource	Service	404	INFO	No	Yes
Illegal transition	Domain	400	INFO	No	N/A
Version conflict	OCC	409	INFO	Yes	N/A
Idempotency key conflict	Idempotency table	409	INFO	No	Yes
DB constraint conflict	IntegrityError	409	WARNING	Depends	N/A
DB unavailable	Infra	503	ERROR	Yes	N/A
Timeout	Middleware/gateway	504	ERROR	Yes	N/A
Partial transaction	session.begin()	500/409/400	ERROR	Depends	N/A

Each failure logged once.

7. Transaction Model

All mutations use:

with session.begin():

Atomic guarantees:

State change + version bump atomic

Update + version bump atomic

Partial transaction errors are mapped to the deterministic error corresponding to the triggering condition; no partial writes persist.

DB constraints:

PK on documents.id

Unique constraint on idempotency_keys.key

Isolation:

Postgres READ COMMITTED

8. Concurrency Model

Optimistic locking via integer version

Client must supply If-Match

Mismatch → 409 version_conflict

First writer wins

Create idempotency enforced via Idempotency-Key

9. Observability

Structured JSON logs:

Fields:

timestamp

level

request_id

method

path

status_code

error_code

Health:

/health/live

/health/ready (DB SELECT 1)

10. Constraints

Backend Stack Profile v1.0 enforced.

Pinned:

Python 3.12

FastAPI

Pydantic v2

SQLAlchemy 2.x

PostgreSQL

Alembic

pytest

ruff / black / mypy

GitHub Actions

Docker (pinned image)

No new dependency without spec update.

11. Complexity Budget

Max endpoints: 9

Max entities: 1 + idempotency table

Max background processes: 0

Target LOC: 2.5k–3.2k

Max layers: 3

12. Testing Strategy

Unit:

Legal transitions

Illegal transitions

Terminal state protections

Integration:

Full workflow happy paths

Idempotent create semantics

Version conflict

Not found

Error envelope

Migration:

Upgrade + downgrade in CI

Coverage:

80–85%

13. Security Considerations

Auth: out of scope
Authorization: out of scope
Secrets via environment variables
No secret logging

14. Operational Considerations

Env vars:

DATABASE_URL

APP_ENV

LOG_LEVEL

Startup:

DB up

Migrate

Run

Rollback:

Alembic downgrade supported

15. Tradeoffs

No auth → preserve scope
No PATCH → avoid partial semantics
No list endpoints → avoid fake scale
No audit → preserve simplicity

10x scale:

Add list endpoints

Add metrics/tracing

Add auth

Add stronger operational tuning

First failure:
Client misuse of If-Match versioning.

16. Definition of Done

Spec complete

Scope frozen

Freeze committed

Tests passing

CI green

No TODOs

Interview defense written

17. Risk Register

Idempotency correctness → request_hash enforcement
Concurrency edges → OCC + integration tests
DB masking → readiness check
Scope creep → freeze discipline

Owner: Jeff Smith
Date: 2026-02-21