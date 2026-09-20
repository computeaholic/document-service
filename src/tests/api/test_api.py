"""API layer tests."""

import logging
from collections.abc import Callable
from types import TracebackType
from typing import Any

from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from sqlalchemy.exc import ProgrammingError

from api.app import create_app


def test_create_document_returns_201_with_id_and_status() -> None:
    """Test POST /documents returns 201 with document metadata."""
    app = create_app()
    client = TestClient(app)
    response = client.post(
        "/documents",
        json={"title": "Test", "content": "Body"},
        headers={"Idempotency-Key": "test-create-1"},
    )

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] == "draft"


def test_create_document_with_valid_title_and_content() -> None:
    """Test creating a document with valid input returns 201."""
    app = create_app()
    client = TestClient(app)
    response = client.post(
        "/documents",
        json={"title": "My Document", "content": "Content here"},
        headers={"Idempotency-Key": "test-create-2"},
    )

    assert response.status_code == 201
    data = response.json()
    assert len(data["id"]) > 0
    assert data["title"] == "My Document"


def test_create_document_with_empty_title_returns_422() -> None:
    """Test POST /documents with empty title returns 422 (Pydantic validation)."""
    app = create_app()
    client = TestClient(app)
    response = client.post(
        "/documents",
        json={"title": "", "content": "Body"},
        headers={"Idempotency-Key": "test-create-3"},
    )

    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "validation_error"


def test_create_document_with_whitespace_title_returns_422() -> None:
    """Test POST /documents with whitespace-only title returns 422 (domain validation)."""
    app = create_app()
    client = TestClient(app)
    response = client.post(
        "/documents",
        json={"title": "   ", "content": "Body"},
        headers={"Idempotency-Key": "test-create-4"},
    )

    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "validation_error"


def test_create_document_with_empty_content_returns_201() -> None:
    """Test POST /documents with empty content returns 201 (allowed)."""
    app = create_app()
    client = TestClient(app)
    response = client.post(
        "/documents",
        json={"title": "Title", "content": ""},
        headers={"Idempotency-Key": "test-create-5"},
    )

    assert response.status_code == 201


def test_get_document_returns_200_with_full_document() -> None:
    """Test GET /documents/{doc_id} returns 200 with full document."""
    app = create_app()
    client = TestClient(app)
    create_response = client.post(
        "/documents",
        json={"title": "Test", "content": "Body"},
        headers={"Idempotency-Key": "test-create-6"},
    )
    assert create_response.status_code == 201
    doc_id = create_response.json()["id"]

    get_response = client.get(f"/documents/{doc_id}")

    assert get_response.status_code == 200
    data = get_response.json()
    assert data["id"] == doc_id
    assert data["title"] == "Test"
    assert data["content"] == "Body"
    assert data["status"] == "draft"
    assert data["version"] == 0


def test_get_nonexistent_document_returns_404() -> None:
    """Test GET /documents/{doc_id} with invalid ID returns 404."""
    app = create_app()
    client = TestClient(app)
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/documents/{fake_id}")

    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "not_found"


def test_create_and_retrieve_document_flow() -> None:
    """Test create then retrieve document flow."""
    app = create_app()
    client = TestClient(app)
    create_response = client.post(
        "/documents",
        json={"title": "Workflow", "content": "Test content"},
        headers={"Idempotency-Key": "test-create-7"},
    )
    assert create_response.status_code == 201
    doc_id = create_response.json()["id"]

    get_response = client.get(f"/documents/{doc_id}")
    assert get_response.status_code == 200

    data = get_response.json()
    assert data["title"] == "Workflow"
    assert data["content"] == "Test content"


def test_response_schema_includes_all_fields() -> None:
    """Test response includes all required fields."""
    app = create_app()
    client = TestClient(app)
    response = client.post(
        "/documents",
        json={"title": "Test", "content": "Content"},
        headers={"Idempotency-Key": "test-create-8"},
    )

    data = response.json()
    assert "id" in data
    assert "title" in data
    assert "content" in data
    assert "status" in data
    assert "version" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_update_document_returns_200_with_incremented_version() -> None:
    """Test PUT /documents/{doc_id} updates and increments version."""
    app = create_app()
    client = TestClient(app)
    create_response = client.post(
        "/documents",
        json={"title": "Original", "content": "Original content"},
        headers={"Idempotency-Key": "test-create-9"},
    )
    doc_id = create_response.json()["id"]

    update_response = client.put(
        f"/documents/{doc_id}",
        json={"title": "Updated", "content": "Updated content"},
        headers={"If-Match": "0"},
    )

    assert update_response.status_code == 200
    data = update_response.json()
    assert data["title"] == "Updated"
    assert data["content"] == "Updated content"
    assert data["version"] == 1


def test_update_document_with_version_mismatch_returns_409() -> None:
    """Test PUT /documents/{doc_id} with wrong version returns 409."""
    app = create_app()
    client = TestClient(app)
    create_response = client.post(
        "/documents",
        json={"title": "Original", "content": "Original content"},
        headers={"Idempotency-Key": "test-create-10"},
    )
    doc_id = create_response.json()["id"]

    response = client.put(
        f"/documents/{doc_id}",
        json={"title": "Updated", "content": "Updated content"},
        headers={"If-Match": "99"},
    )

    assert response.status_code == 409
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "version_conflict"


def test_update_document_without_if_match_returns_422() -> None:
    """Test PUT /documents/{doc_id} without If-Match header returns 422."""
    app = create_app()
    client = TestClient(app)
    create_response = client.post(
        "/documents",
        json={"title": "Original", "content": "Original content"},
        headers={"Idempotency-Key": "test-create-11"},
    )
    doc_id = create_response.json()["id"]

    response = client.put(
        f"/documents/{doc_id}",
        json={"title": "Updated", "content": "Updated content"},
    )

    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "validation_error"


def test_update_nonexistent_document_returns_404() -> None:
    """Test PUT /documents/{doc_id} with nonexistent ID returns 404."""
    app = create_app()
    client = TestClient(app)
    fake_id = "00000000-0000-0000-0000-000000000000"

    response = client.put(
        f"/documents/{fake_id}",
        json={"title": "Title", "content": "Content"},
        headers={"If-Match": "0"},
    )

    assert response.status_code == 404


def test_submit_document_returns_200_with_submitted_status() -> None:
    """Test POST /documents/{doc_id}/submit returns 200 with submitted status."""
    app = create_app()
    client = TestClient(app)
    create_response = client.post(
        "/documents",
        json={"title": "Test", "content": "Body"},
        headers={"Idempotency-Key": "test-create-12"},
    )
    doc_id = create_response.json()["id"]

    submit_response = client.post(
        f"/documents/{doc_id}/submit",
        headers={"If-Match": "0"},
    )

    assert submit_response.status_code == 200
    data = submit_response.json()
    assert data["status"] == "submitted"
    assert data["version"] == 1


def test_submit_then_approve_returns_approved_status() -> None:
    """Test submit then approve flow."""
    app = create_app()
    client = TestClient(app)
    create_response = client.post(
        "/documents",
        json={"title": "Test", "content": "Body"},
        headers={"Idempotency-Key": "test-create-13"},
    )
    doc_id = create_response.json()["id"]

    client.post(f"/documents/{doc_id}/submit", headers={"If-Match": "0"})
    approve_response = client.post(
        f"/documents/{doc_id}/approve",
        headers={"If-Match": "1"},
    )

    assert approve_response.status_code == 200
    data = approve_response.json()
    assert data["status"] == "approved"
    assert data["version"] == 2


def test_submit_twice_returns_400_illegal_transition() -> None:
    """Test submitting twice returns 400 illegal transition."""
    app = create_app()
    client = TestClient(app)
    create_response = client.post(
        "/documents",
        json={"title": "Test", "content": "Body"},
        headers={"Idempotency-Key": "test-create-14"},
    )
    doc_id = create_response.json()["id"]

    client.post(f"/documents/{doc_id}/submit", headers={"If-Match": "0"})
    conflict_response = client.post(
        f"/documents/{doc_id}/submit",
        headers={"If-Match": "1"},
    )

    assert conflict_response.status_code == 400
    data = conflict_response.json()
    assert "error" in data
    assert data["error"]["code"] == "illegal_transition"


def test_approve_draft_returns_400_illegal_transition() -> None:
    """Test approving a draft document returns 400 illegal transition."""
    app = create_app()
    client = TestClient(app)
    create_response = client.post(
        "/documents",
        json={"title": "Test", "content": "Body"},
        headers={"Idempotency-Key": "test-create-15"},
    )
    doc_id = create_response.json()["id"]

    conflict_response = client.post(
        f"/documents/{doc_id}/approve",
        headers={"If-Match": "0"},
    )

    assert conflict_response.status_code == 400
    data = conflict_response.json()
    assert "error" in data
    assert data["error"]["code"] == "illegal_transition"


def test_submit_nonexistent_document_returns_404() -> None:
    """Test submitting nonexistent document returns 404."""
    app = create_app()
    client = TestClient(app)
    fake_id = "00000000-0000-0000-0000-000000000000"

    response = client.post(
        f"/documents/{fake_id}/submit",
        headers={"If-Match": "0"},
    )

    assert response.status_code == 404


def test_submit_then_reject_returns_rejected_status() -> None:
    """Test submit then reject flow."""
    app = create_app()
    client = TestClient(app)
    create_response = client.post(
        "/documents",
        json={"title": "Test", "content": "Body"},
        headers={"Idempotency-Key": "test-create-16"},
    )
    doc_id = create_response.json()["id"]

    client.post(f"/documents/{doc_id}/submit", headers={"If-Match": "0"})
    reject_response = client.post(
        f"/documents/{doc_id}/reject",
        headers={"If-Match": "1"},
    )

    assert reject_response.status_code == 200
    data = reject_response.json()
    assert data["status"] == "rejected"
    assert data["version"] == 2


def test_reject_nonexistent_document_returns_404() -> None:
    """Test rejecting nonexistent document returns 404."""
    app = create_app()
    client = TestClient(app)
    fake_id = "00000000-0000-0000-0000-000000000000"

    response = client.post(
        f"/documents/{fake_id}/reject",
        headers={"If-Match": "0"},
    )

    assert response.status_code == 404


def test_approve_nonexistent_document_returns_404() -> None:
    """Test approving nonexistent document returns 404."""
    app = create_app()
    client = TestClient(app)
    fake_id = "00000000-0000-0000-0000-000000000000"

    response = client.post(
        f"/documents/{fake_id}/approve",
        headers={"If-Match": "0"},
    )

    assert response.status_code == 404


def test_repository_isolation_between_app_instances() -> None:
    """Test repository consistency across app instances."""
    app1 = create_app()
    client1 = TestClient(app1)

    app2 = create_app()
    client2 = TestClient(app2)

    response = client1.post(
        "/documents",
        json={"title": "A", "content": "B"},
        headers={"Idempotency-Key": "test-create-17"},
    )
    doc_id = response.json()["id"]

    response2 = client2.get(f"/documents/{doc_id}")

    assert response2.status_code == 200
    data = response2.json()
    assert data["id"] == doc_id


def test_health_endpoint_returns_ok() -> None:
    """Test /health/live returns ok status."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_endpoint_returns_ready(monkeypatch: MonkeyPatch) -> None:
    """Test /health/ready returns ready when database is available."""

    executed: list[str] = []

    class DummySession:
        def __enter__(self) -> "DummySession":
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> None:
            return None

        def execute(self, statement: str) -> None:
            executed.append(str(statement))

    def fake_get_session_factory() -> Callable[[], DummySession]:
        return lambda: DummySession()

    monkeypatch.setattr("api.app.get_session_factory", fake_get_session_factory)
    app = create_app()
    client = TestClient(app)

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
    assert len(executed) == 2


def test_readiness_endpoint_returns_503_on_failure(
    monkeypatch: MonkeyPatch,
) -> None:
    """Test /health/ready returns 503 when database is unavailable."""

    def fake_get_session_factory() -> Callable[[], object]:
        raise RuntimeError("db down")

    app = create_app()
    monkeypatch.setattr("api.app.get_session_factory", fake_get_session_factory)
    client = TestClient(app)

    response = client.get("/health/ready")

    assert response.status_code == 503
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "db_unavailable"


def test_readiness_endpoint_returns_503_when_schema_is_missing(
    monkeypatch: MonkeyPatch,
) -> None:
    """Test /health/ready returns 503 when the application schema is unavailable."""

    class DummySession:
        def __enter__(self) -> "DummySession":
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> None:
            return None

        def execute(self, statement: str) -> None:
            raise ProgrammingError(str(statement), {}, Exception("missing table"))

    def fake_get_session_factory() -> Callable[[], DummySession]:
        return lambda: DummySession()

    monkeypatch.setattr("api.app.get_session_factory", fake_get_session_factory)
    app = create_app()
    client = TestClient(app)

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "db_unavailable",
            "message": "Database unavailable",
        }
    }


def test_request_id_appears_in_logs(monkeypatch: MonkeyPatch) -> None:
    """Test that every request gets a unique request_id logged."""
    logged_calls: list[dict[str, Any]] = []

    def capture_info(message: str, *args: object, **kwargs: Any) -> None:
        logged_calls.append({"message": message, "kwargs": kwargs})

    app = create_app()
    monkeypatch.setattr(logging.getLogger("document_service"), "info", capture_info)
    client = TestClient(app)

    response = client.post(
        "/documents",
        json={"title": "Test", "content": "Body"},
        headers={"Idempotency-Key": "test-create-18"},
    )

    assert response.status_code == 201

    assert any(
        "request_id" in call["kwargs"].get("extra", {}) for call in logged_calls
    ), "No request_id found in captured logger calls"


def test_error_logged_once_with_request_id(monkeypatch: MonkeyPatch) -> None:
    """Test that errors are logged exactly once at API boundary with request_id."""
    logged_calls: list[dict[str, Any]] = []

    def capture_info(message: str, *args: object, **kwargs: Any) -> None:
        logged_calls.append({"message": message, "kwargs": kwargs})

    app = create_app()
    monkeypatch.setattr(logging.getLogger("document_service"), "info", capture_info)
    client = TestClient(app)

    # Create document
    response = client.post(
        "/documents",
        json={"title": "Test Doc", "content": "Test content"},
        headers={"Idempotency-Key": "test-create-19"},
    )
    assert response.status_code == 201

    logged_calls.clear()

    # Trigger ValidationError (empty title after trim)
    update_response = client.post(
        "/documents",
        json={"title": "  ", "content": "Content"},
        headers={"Idempotency-Key": "test-create-20"},
    )
    assert update_response.status_code == 422

    error_logs = [
        call["kwargs"]["extra"]
        for call in logged_calls
        if isinstance(call["kwargs"].get("extra"), dict)
        and call["kwargs"]["extra"].get("error_code") == "validation_error"
    ]

    # Should have exactly one error log
    assert (
        len(error_logs) == 1
    ), f"Expected 1 error log, found {len(error_logs)}: {error_logs}"

    # Verify required fields
    error_log = error_logs[0]
    assert "request_id" in error_log, "request_id missing from error log"
    assert "error_code" in error_log, "error_code missing from error log"
    assert error_log["error_code"] == "validation_error"
    assert error_log["status_code"] == 422
