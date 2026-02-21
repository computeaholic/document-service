Interview Defense — document-service
1. Design Intent

document-service manages a single Document entity through a constrained approval workflow (draft → submitted → approved/rejected). The system is responsible for enforcing state legality, preventing lost updates, and ensuring atomic mutations under concurrent access. The primary invariant protected is that no illegal state transition or partial mutation may persist. The most important design decision was enforcing optimistic concurrency via explicit version matching combined with mandatory transaction boundaries. The system is intentionally narrow to isolate correctness, failure modeling, and transactional discipline.

2. What This Project Demonstrates

Explicit state transition enforcement in a framework-agnostic domain layer.

Illegal transitions raising deterministic domain exceptions.

Mandatory optimistic concurrency via integer version and If-Match header.

Atomic mutation boundaries using with session.begin():.

Idempotent create operation enforced through a dedicated idempotency table and unique constraint.

Deterministic error envelope mapping at API boundary.

Explicit failure matrix with test coverage for each failure class.

Clear dependency direction: api → services → domain.

CI-enforced lint, type checking, and test coverage thresholds.

All listed behaviors are implemented and tested.

3. Tradeoffs Made
Decision	Alternative Considered	Why Rejected	Cost of This Choice
Optimistic locking	Pessimistic row locks	Increases transaction scope and coupling	Client must handle version conflicts
Dedicated idempotency table	Unique constraints only	Cannot detect payload mismatch	Additional table and request hashing
No background jobs	Async queue/outbox	Adds operational and failure complexity	No async extensibility
No authentication	JWT/OAuth	Not core to state discipline signal	Not production-secure
No list endpoint	Pagination/filtering	Adds query complexity unrelated to workflow	Cannot browse dataset
Deterministic error envelope	Framework defaults	Inconsistent error shapes	Custom exception mapping layer

These are intentional boundary decisions.

4. Scaling Considerations (10x Scenario)

First bottleneck:
Write contention on the same document (version conflicts increase).

Mitigation:
Client-side retry with backoff; DB pool tuning.

Next bottleneck:
Single Postgres instance throughput.

Mitigation:
Add read replica for GET endpoints; increase connection pool; optimize indexes if list endpoint introduced.

First extraction boundary:
Extract idempotency and workflow logic into reusable internal module if multiple entities introduced.

Stable components at 10x:

Domain state machine

Error contract

Concurrency semantics

Transaction model

No distributed architecture required unless multi-node deployment introduced.

5. Concurrency & Failure Analysis

Race conditions occur at:

Concurrent updates to the same document.

Concurrent create with same idempotency key.

Prevention:

Version check (If-Match) prevents lost updates.

Unique constraint on idempotency key prevents duplicate create.

First writer wins; second receives 409.

Partial failure risk:

Any exception inside session.begin().

Mitigation:

Atomic rollback guarantees no partial state persists.

Idempotency guarantees:

Same key + same payload returns original document.

Same key + different payload returns 409.

Retry safety:

Safe: GET, create (with idempotency key), version conflict after refresh.

Unsafe: Blind retry of mutation without refreshing version.

All behaviors are deterministic and test-backed.

6. Operational Readiness

Startup:

Start Postgres via docker-compose.

Run make migrate.

Run make run.

Migrations:

Managed via Alembic.

Upgrade and downgrade validated in CI.

Health endpoints:

/health/live — process running.

/health/ready — DB connectivity verified.

Logs during failure:

Structured JSON.

Single log entry per failure.

Includes route, request_id, status_code, error_code.

Failed deployment recovery:

Roll back to previous container image.

Run Alembic downgrade if schema changed.

No hidden operational assumptions.

7. Known Limits

Single Postgres instance assumption.

No horizontal scaling implemented.

No authentication or authorization.

No audit trail.

No distributed locking.

No rate limiting.

No list/pagination endpoint.

No background processing.

No caching layer.

These limits are intentional to preserve clarity and signal discipline.

This project is not optimized for feature breadth.

It is optimized for correctness under constraint.