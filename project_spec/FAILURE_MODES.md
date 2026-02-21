Failure Modes — document-service

All failure scenarios are explicitly defined below.

No unmodeled failure is acceptable.

Failure behavior is deterministic and enforced at the API boundary.

Failure Matrix
Scenario	Detected At	User Response	HTTP Code	Log Level	Retry Strategy	Idempotent Behavior
Invalid input (schema)	Validation layer (Pydantic)	validation_error envelope	422	INFO	No retry	N/A
Invalid UUID format	Validation layer	validation_error	422	INFO	No retry	N/A
Missing resource	Service layer (lookup)	not_found	404	INFO	No retry	Safe
Illegal transition	Domain layer	illegal_transition	400	INFO	No retry	N/A
Duplicate submission (e.g. approve approved doc)	Domain layer	illegal_transition	400	INFO	No retry	N/A
Concurrency conflict (version mismatch)	Service layer (version compare)	version_conflict	409	INFO	Client refresh + retry	Safe if client re-fetches
Duplicate idempotency key (same payload)	Infrastructure layer (idempotency table)	Return original resource	200/201	INFO	Safe	Safe
Duplicate idempotency key (different payload)	Infrastructure layer	idempotency_key_conflict	409	INFO	No retry	Protected by constraint
Database constraint conflict	Infrastructure layer (IntegrityError)	db_conflict	409	WARNING	No retry	Protected by DB
Database unavailable	Infrastructure layer (connection failure)	db_unavailable	503	ERROR	Retry with backoff	N/A
Timeout (request processing)	API boundary (middleware/gateway)	timeout	504	ERROR	Retry with backoff	N/A
Partial transaction failure	Service layer (inside transaction)	Deterministic mapped error	400/409/500	ERROR	Depends on error	Atomic rollback
Unexpected internal exception	API boundary exception handler	internal_error	500	ERROR	Retry only if safe	N/A
Missing Idempotency-Key header (create)	Validation layer	validation_error	422	INFO	No retry	N/A
Missing If-Match header (mutation)	Validation layer	validation_error	422	INFO	No retry	N/A
Submit with empty content	Domain layer	illegal_transition	400	INFO	No retry	N/A
Attempt mutation on terminal state	Domain layer	illegal_transition	400	INFO	No retry	N/A
Health check DB failure	Infrastructure layer	db_unavailable	503	ERROR	Retry after DB restore	N/A
External dependency failure	Not applicable	N/A	N/A	N/A	N/A	N/A
Background job failure	Not applicable	N/A	N/A	N/A	N/A	N/A
Failure Definitions

Below are explicit definitions and behavioral expectations.

1. Invalid Input

Detected At: Validation layer
User Response:

{
  "error": {
    "code": "validation_error",
    "message": "field-specific validation message"
  }
}

Log Level: INFO
Retry Strategy: No retry (client must correct input)
Idempotent Behavior: Not applicable

2. Missing Resource

Detected At: Service layer during lookup

User Response:

{
  "error": {
    "code": "not_found",
    "message": "document not found"
  }
}

Log Level: INFO
Retry Strategy: No retry
Idempotent Behavior: Safe to retry GET

3. Illegal Transition

Examples:

draft → approve

submitted → draft

approved → any

Detected At: Domain layer

User Response:

{
  "error": {
    "code": "illegal_transition",
    "message": "cannot approve document in state draft"
  }
}

Log Level: INFO
Retry Strategy: No retry
Idempotent Behavior: Not applicable

Illegal transitions must be exhaustively tested.

4. Concurrency Conflict

Occurs when If-Match version does not equal current persisted version.

Detected At: Service layer

User Response:

{
  "error": {
    "code": "version_conflict",
    "message": "document version mismatch"
  }
}

HTTP Code: 409

Log Level: INFO
Retry Strategy:

Client must re-fetch document

Retry with updated version

Idempotent Behavior: Safe if client refreshes first

5. Idempotency Key Conflict

Same key + different payload.

Detected At: Infrastructure layer

User Response:

{
  "error": {
    "code": "idempotency_key_conflict",
    "message": "idempotency key reused with different payload"
  }
}

HTTP Code: 409
Log Level: INFO
Retry Strategy: No retry
Idempotent Behavior: Protected by DB constraint

6. Database Unavailable

Connection refused, pool exhaustion, network failure.

Detected At: Infrastructure layer

User Response:

{
  "error": {
    "code": "db_unavailable",
    "message": "database unavailable"
  }
}

HTTP Code: 503
Log Level: ERROR
Retry Strategy: Retry with exponential backoff
Idempotent Behavior: Safe for GET, create protected by idempotency

7. Timeout

Request exceeds processing window.

Detected At: API boundary

User Response:

{
  "error": {
    "code": "timeout",
    "message": "request timed out"
  }
}

HTTP Code: 504
Log Level: ERROR
Retry Strategy: Retry with backoff
Idempotent Behavior: Create safe due to idempotency key

8. Partial Transaction Failure

Exception thrown inside session.begin().

Behavior:

Entire transaction rolls back.

No partial state persisted.

Error mapped to:

400 (domain)

409 (constraint)

500 (unexpected)

Detected At: Service layer

Log Level: ERROR
Retry Strategy: Depends on mapped error
Idempotent Behavior: Atomic rollback guarantees consistency

9. Unexpected Internal Exception

Bug or unhandled edge case.

Detected At: API exception handler

User Response:

{
  "error": {
    "code": "internal_error",
    "message": "unexpected server error"
  }
}

HTTP Code: 500
Log Level: ERROR
Retry Strategy: Retry only if safe
Idempotent Behavior: Depends on operation

Stack traces are never exposed to clients.

Enforcement Rules

Every endpoint maps to at least one failure scenario.

Every state transition defines illegal transition behavior.

Every failure in this matrix must have at least one test.

No silent failure is allowed.

No failure may bypass the error envelope.

Errors are logged exactly once.

Failure handling is part of the architecture.

It is not optional.
It is not reactive.
It is deliberate and test-backed.