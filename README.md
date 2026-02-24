# Document Service

Production-grade REST API for document lifecycle management with strict concurrency controls and operational guarantees.

## Architecture

**Domain-Driven Design** with strict layer separation:
- **Domain**: Pure business logic (`Document` aggregate, state transitions)
- **Application**: Service layer and repository interfaces
- **Infrastructure**: Persistence implementations (in-memory, PostgreSQL)
- **API**: FastAPI HTTP interface with error envelope, middleware, OpenAPI

**Key Components**:
- **Error Envelope**: Uniform `{"error": {"code": "...", "message": "...", "details": {...}}}` across all 4xx/5xx responses
- **Concurrency Control**: Optimistic locking via `If-Match` header (required for PUT)
- **Idempotency**: `Idempotency-Key` header support on POST with 24-hour key expiration
- **Structured Logging**: JSON logs with `request_id`, `method`, `path`, `status_code`, `error_code`
- **Health Endpoints**: `/health/live` (always 200), `/health/ready` (validates DB connection)

## API Contract

### Document States
```
draft → review → published
         ↓
      archived
```

**Immutable Rules**:
- `draft` can transition to `review` or `archived`
- `review` can transition to `published` or `archived`
- `published` can only transition to `archived`
- `archived` is terminal (no transitions allowed)

### Endpoints

#### POST /documents
**Request**:
```json
{
  "title": "string (1-200 chars)",
  "content": "string (1-10000 chars)"
}
```
**Response** (201):
```json
{
  "id": "uuid",
  "title": "string",
  "content": "string",
  "status": "draft",
  "version": 1,
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
  "status": "draft|review|published|archived",
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
  "content": "string (1-10000 chars)",
  "status": "draft|review|published|archived"
}
```
**Response** (200): Same as GET

**Errors**:
- `412 PRECONDITION_FAILED`: If-Match version mismatch (concurrent modification)
- `422 VALIDATION_ERROR`: Invalid field values
- `409 ILLEGAL_TRANSITION`: Invalid state transition

#### DELETE /documents/{id}
**Response** (204): No content

### Error Codes
- `VALIDATION_ERROR` (422): Pydantic validation failure
- `ILLEGAL_TRANSITION` (409): Invalid document state transition
- `NOT_FOUND` (404): Document does not exist
- `PRECONDITION_FAILED` (412): If-Match version conflict
- `SERVICE_UNAVAILABLE` (503): Database connectivity failure

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

## CI/CD

GitHub Actions workflow enforces:
- Ruff linting (zero violations)
- Mypy type checking (strict mode)
- pytest with ≥80% coverage (currently 96%)
- Alembic migration smoke tests (forward + backward + forward)

## Governance

This repository is under **FREEZE** governance. See [FREEZE.md](FREEZE.md) for scope boundaries and architectural rules.
