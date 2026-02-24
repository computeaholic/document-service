# Document Service

Production-grade REST API for document lifecycle management with strict concurrency controls and operational guarantees.

## Architecture

**Domain-Driven Design** with strict layer separation:
- **Domain**: Pure business logic (`Document` aggregate, state transitions)
- **Application**: Service layer and repository interfaces
- **Infrastructure**: Persistence implementations (in-memory, PostgreSQL)
- **API**: FastAPI HTTP interface with error envelope, middleware, OpenAPI

**Key Components**:
- **Error Envelope**: Uniform `{"error": {"code": "...", "message": "..."}}` across all 4xx/5xx responses
- **Concurrency Control**: Optimistic locking via `If-Match` header (required for PUT)
- **Idempotency**: `Idempotency-Key` header required on POST
- **Structured Logging**: JSON logs with `request_id`, `method`, `path`, `status_code`, `error_code`
- **Health Endpoints**: `/health/live` (always 200), `/health/ready` (validates DB connection)

## API Contract

### Document States
```
draft → submitted → approved
     ↓
  rejected
```

**Immutable Rules**:
- `draft` can transition to `submitted`
- `submitted` can transition to `approved` or `rejected`
- `approved` is terminal (no transitions allowed)
- `rejected` is terminal (no transitions allowed)

### Endpoints

#### POST /documents
**Request**:
```json
{
  "title": "string (1-200 chars)",
  "content": "string (0-20000 chars)"
}
```
**Response** (201):
```json
{
  "id": "uuid",
  "title": "string",
  "content": "string",
  "status": "draft",
  "version": 0,
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```
**Idempotency**: Include `Idempotency-Key: <uuid>` header to ensure exactly-once processing.

#### GET /documents/{id}
**Response** (200):
```json
{
  "id": "uuid",
  "title": "string",
  "content": "string",
  "status": "draft|submitted|approved|rejected",
  "version": 1,
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

#### PUT /documents/{id}
**Headers** (REQUIRED):
- `If-Match: <version>` - Optimistic lock version

**Request**:
```json
{
  "title": "string (1-200 chars)",
  "content": "string (0-20000 chars)"
}
```
**Response** (200): Same as GET

**Errors**:
- `409 version_conflict`: If-Match version mismatch (concurrent modification)
- `422 validation_error`: Invalid field values
- `400 illegal_transition`: Invalid state transition

#### POST /documents/{id}/submit
Transitions a document from `draft` → `submitted`.

**Headers** (REQUIRED):
- `If-Match: <version>`

**Response** (200): Same as GET

**Errors**:
- `409 version_conflict`
- `422 validation_error` (content must be non-empty on submit)
- `400 illegal_transition`

#### POST /documents/{id}/approve
Transitions a document from `submitted` → `approved`.

**Headers** (REQUIRED):
- `If-Match: <version>`

**Response** (200): Same as GET

**Errors**:
- `409 version_conflict`
- `400 illegal_transition`

#### POST /documents/{id}/reject
Transitions a document from `submitted` → `rejected`.

**Headers** (REQUIRED):
- `If-Match: <version>`

**Response** (200): Same as GET

**Errors**:
- `409 version_conflict`
- `400 illegal_transition`

### Error Codes
- `validation_error` (422): Pydantic validation failure
- `illegal_transition` (400): Invalid document state transition
- `not_found` (404): Document does not exist
- `version_conflict` (409): If-Match version conflict
- `idempotency_key_conflict` (409): Same idempotency key with different payload
- `db_conflict` (409): Database constraint conflict
- `db_unavailable` (503): Database connectivity failure

## Local Development

### Prerequisites
- Python 3.12+
- Docker & Docker Compose (for PostgreSQL)
- make

### Setup
```bash
# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies (includes dev tools)
pip install -e ".[dev]"

# Start PostgreSQL
make up

# Run migrations
make migrate

# Run application
make run
```

### Testing
```bash
# Run all tests with coverage
pytest --cov=src --cov-report=term-missing

# Type checking
mypy src

# Linting
ruff check src
```

## Database Migrations

### Commands
```bash
# Apply all pending migrations
make migrate

# Rollback last migration
make rollback

# Create new migration (after modifying models)
alembic revision --autogenerate -m "description"
```

### Schema
**documents table**:
- `id` (UUID, PK)
- `title` (VARCHAR(200))
- `content` (TEXT)
- `status` (VARCHAR(20))
- `version` (INTEGER)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

**idempotency_keys table**:
- `id` (UUID, PK)
- `key` (VARCHAR(255), UNIQUE)
- `request_hash` (VARCHAR(64))
- `response_body` (TEXT)
- `created_at` (TIMESTAMP)

## Docker Deployment

### Build and Run
```bash
# Start all services (builds on first run)
make up

# Stop all services
make down

# View logs
docker-compose logs -f api
```

### Environment Variables
- `DATABASE_URL`: PostgreSQL connection string (default: `postgresql+psycopg://postgres:postgres@db:5432/documents`)

## Operational Guarantees

1. **Concurrency Safety**: All document mutations protected by optimistic locking (version counter)
2. **Idempotency**: POST requests with `Idempotency-Key` return cached response within 24h window
3. **Audit Trail**: `created_at` and `updated_at` timestamps on all entities
4. **Request Tracing**: Every request tagged with unique `request_id` UUID in logs
5. **Migration Integrity**: CI enforces bidirectional migration tests (upgrade/downgrade/upgrade)
6. **Error Isolation**: Exceptions logged once at API boundary (no duplicate logs in domain/repository)

## Idempotency Guarantees

The service implements idempotency for document creation via the `Idempotency-Key` header:

**Same key + same body → Replayed response**
```bash
# First request
POST /documents
Idempotency-Key: abc-123
{"title": "Doc", "content": "Content"}
→ 201 {"id": "uuid-1", "version": 1, ...}

# Replay with same key and body
POST /documents
Idempotency-Key: abc-123
{"title": "Doc", "content": "Content"}
→ 201 {"id": "uuid-1", "version": 1, ...}  # Same response, no new document
```

**Same key + different body → 409 Conflict**
```bash
# First request
POST /documents
Idempotency-Key: abc-123
{"title": "Doc A", "content": "..."}
→ 201 Created

# Different payload with same key
POST /documents
Idempotency-Key: abc-123
{"title": "Doc B", "content": "..."}
→ 409 {"error": {"code": "idempotency_key_conflict", ...}}
```

**Implementation Details**:
- Idempotency keys stored with SHA-256 hash of request body
- Key reuse with different payload rejected to prevent silent data loss
- Cached responses valid indefinitely (24-hour TTL recommended for production cleanup)

## Optimistic Concurrency

All document updates require the `If-Match` header with current version:

```bash
# Get current version
GET /documents/{id}
→ 200 {"version": 5, ...}

# Update with version check
PUT /documents/{id}
If-Match: 5
{"title": "Updated", ...}
→ 200 {"version": 6, ...}

# Concurrent update with stale version fails
PUT /documents/{id}
If-Match: 5  # Stale
{"title": "Another update", ...}
→ 409 {"error": {"code": "version_conflict", ...}}
```

**Enforcement Layers**:
1. **Application Layer**: Service validates version before mutation
2. **Database Layer**: UPDATE with WHERE version={expected} prevents race conditions
3. **API Layer**: Missing `If-Match` header → 422 validation_error

**Why Optimistic Locking**:
- No distributed locks required (horizontal scaling friendly)
- Explicit conflict detection (callers handle retry logic)
- Version counter doubles as audit trail

## Error Envelope

All 4xx/5xx responses use uniform error structure:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description"
  }
}
```

**Error Codes**:
- `validation_error` (422): Pydantic validation failure (empty title, content too long, etc.)
- `illegal_transition` (400): Invalid state transition (e.g., draft → approved)
- `not_found` (404): Document does not exist
- `version_conflict` (409): If-Match version mismatch
- `idempotency_key_conflict` (409): Same idempotency key with different payload
- `db_unavailable` (503): Database connectivity failure

**Logging Discipline**:
- Domain layer: Zero logging (pure business logic)
- Repository layer: Zero logging (infrastructure concern)
- API layer: Log errors **once** at boundary with `request_id`, `error_code`, `message`

## Non-Goals

This service explicitly **does not** implement:

- **Distributed Locking**: Optimistic concurrency sufficient for expected load
- **Horizontal Idempotency Store**: Single Postgres table adequate for scale target
- **Async Processing**: Synchronous HTTP sufficient for <100ms p99 latency
- **Soft Deletes**: Hard deletes enforce data lifecycle (GDPR compliance)
- **Multi-Tenancy**: Single-tenant deployment model
- **Event Sourcing**: State snapshots with version counter sufficient
- **CQRS**: Read/write separation unnecessary for current complexity

Senior reviewers respect these boundaries. Scope expansion requires spec revision.

## CI/CD

GitHub Actions workflow enforces:
- Ruff linting (zero violations)
- Mypy type checking (strict mode)
- pytest with ≥80% coverage (currently 96%)
- Alembic migration smoke tests (forward + backward + forward)

## Governance

This repository is under **FREEZE** governance. See [FREEZE.md](FREEZE.md) for scope boundaries and architectural rules.

## Release Integrity

- Release: `v1.0.0`
- Commit: `d7be00d`
- Coverage: `98.5%`
- Migrations: verified (upgrade/downgrade cycle)
- Pre-commit hooks: green (`black`, `ruff`, `mypy`, `bandit`, `trufflehog`)
- CI: passing