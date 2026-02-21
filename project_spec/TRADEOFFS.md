Tradeoffs — document-service

This document records intentional choices and rejected alternatives.

All major design decisions must appear here.

1. Decision Log
Decision	Alternatives Considered	Why Rejected	Cost of This Choice	Where Enforced
Single-table schema for Document	Normalized multi-table workflow model	Unnecessary for single-entity system; adds joins and complexity	Limits extensibility for richer workflows	SPEC_PACK §3, migrations
Optimistic locking via integer version	Pessimistic locking (SELECT FOR UPDATE), DB row locks, no locking	Pessimistic locking increases coupling and transaction scope; no locking unsafe	Requires client discipline with If-Match	SPEC_PACK §8
If-Match header required for mutations	Implicit version in body, server-side auto-merge	Implicit semantics reduce clarity; auto-merge hides conflicts	Clients must manage version explicitly	API contract
Idempotency via dedicated table	Rely solely on unique constraints; client-generated IDs	Unique constraints insufficient for payload conflict detection; client IDs shift responsibility outward	Additional table + hash storage	Transaction model
Deterministic error envelope	Framework default error responses	Default responses inconsistent and leak internal details	Requires custom exception mapping layer	API boundary
Explicit transaction boundaries (session.begin())	Implicit commits, ORM autocommit	Hidden commit behavior is non-deterministic	Slightly more boilerplate	Services layer
No background jobs	Async queue, outbox pattern	Adds infrastructure complexity unrelated to core signal	No async capability in this repo	Scope freeze
No authentication	JWT, OAuth, session-based auth	Not relevant to transaction/state modeling objective	System not production-secure	Scope freeze
No list endpoint	Add pagination + filtering	Introduces query tuning and performance concerns	Harder to manually inspect multiple docs	Scope freeze
Structured logging only	Freeform logs	Harder to parse, inconsistent	Slightly more verbose log config	Observability section
READ COMMITTED isolation	SERIALIZABLE isolation	Overkill for single-row OCC use case	Does not protect against logical conflicts outside versioning	Transaction model
No retry logic in service	Automatic server retries	Hidden behavior reduces determinism	Client must retry	Failure matrix
Explicit health and readiness separation	Single health endpoint	Masks DB readiness issues	Slightly more endpoints	Observability section
2. Scope Exclusions (Intentional Non-Build)
Excluded Feature	Why Not Built	Risk / Cost of Exclusion	When It Would Be Added
Authentication / Authorization	Not core to transaction discipline signal	Not secure for public exposure	When real user context exists
Audit logs / history	Adds write amplification + schema complexity	No historical traceability	When compliance or traceability required
Background notifications	Requires queue/outbox	No async behavior	When domain requires external signaling
Pagination / list endpoint	Adds query/index complexity	Cannot browse multiple records easily	When dataset grows
Caching layer	Adds invalidation complexity	Lower read performance under heavy load	When read volume justifies
Event sourcing	Overkill for single entity workflow	No replay capability	When audit + replay required
Distributed coordination	Not required for single instance	Not horizontally scalable	When scaling beyond single DB instance

These exclusions are intentional boundary contracts.

3. Complexity Avoidance

No background processing — avoids async error handling and retry orchestration.

No external queue — avoids operational burden and poison message semantics.

No caching layer — avoids invalidation complexity; correctness prioritized.

No distributed locking — optimistic locking sufficient for single-row updates.

No multi-tenant model — avoids isolation and access control complexity.

No flexible workflow configuration — avoids state explosion.

No retry framework — avoids hidden behavior and emergent retry storms.

No generic base service abstractions — avoids premature abstraction.

No shared utility modules — avoids architectural ambiguity.

The design is intentionally narrow.

4. 10x Scale Notes (Reality-Based)

Bottleneck:

Write contention on single-row updates (version conflict frequency increases).

Mitigation:

Add exponential backoff guidance to clients.

Tune DB connection pool.

Add read replica for GET endpoints.

Add index optimization if list endpoint introduced.

First extraction boundary:

Extract idempotency mechanism and workflow logic into a reusable internal module if additional entities are introduced.

Introduce auth layer if exposing externally.

Introduce outbox pattern if external side effects required.

No distributed architecture required until:

Multiple app instances

Cross-region replication

High-volume write contention

5. Freeze Rule

Any change to a major decision requires:

Update SPEC_PACK.md

Update this TRADEOFFS.md

Update FREEZE.md with new commit hash

Re-freeze scope if scope changed

No silent architecture changes.

Tradeoffs are part of the contract.

They are not commentary.