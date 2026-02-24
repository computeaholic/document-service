"""API layer tests."""

from types import TracebackType
from typing import Callable

import pytest
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from api.app import create_app


def test_create_document_returns_201_with_id_and_status() -> None:
    """Test POST /documents returns 201 with document metadata."""
    app = create_app()
    client = TestClient(app)
    response = client.post(
        "/documents",
        json={"title": "Test", "content": "Body"},
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
    )

    assert response.status_code == 422
    assert "detail" in response.json()


def test_create_document_with_whitespace_title_returns_400() -> None:
    """Test POST /documents with whitespace-only title returns 400 (domain validation)."""
    app = create_app()
    client = TestClient(app)
    response = client.post(
        "/documents",
        json={"title": "   ", "content": "Body"},
    )

    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_create_document_with_empty_content_returns_422() -> None:
    """Test POST /documents with empty content returns 422 (Pydantic validation)."""
    app = create_app()
    client = TestClient(app)
    response = client.post(
        "/documents",
        json={"title": "Title", "content": ""},
    )

    assert response.status_code == 422


def test_get_document_returns_200_with_full_document() -> None:
    """Test GET /documents/{doc_id} returns 200 with full document."""
    app = create_app()
    client = TestClient(app)
    create_response = client.post(
        "/documents",
        json={"title": "Test", "content": "Body"},
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
    assert data["error"]["code"] == "NOT_FOUND"


def test_create_and_retrieve_document_flow() -> None:
    """Test create then retrieve document flow."""
    app = create_app()
    client = TestClient(app)
    create_response = client.post(
        "/documents",
        json={"title": "Workflow", "content": "Test content"},
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


def test_update_document_with_version_mismatch_returns_400() -> None:
    """Test PUT /documents/{doc_id} with wrong version returns 400."""
    app = create_app()
    client = TestClient(app)
    create_response = client.post(
        "/documents",
        json={"title": "Original", "content": "Original content"},
    )
    doc_id = create_response.json()["id"]

    response = client.put(
        f"/documents/{doc_id}",
        json={"title": "Updated", "content": "Updated content"},
        headers={"If-Match": "99"},
    )

    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VERSION_MISMATCH"


def test_update_document_without_if_match_returns_422() -> None:
    """Test PUT /documents/{doc_id} without If-Match header returns 422."""
    app = create_app()
    client = TestClient(app)
    create_response = client.post(
        "/documents",
        json={"title": "Original", "content": "Original content"},
    )
    doc_id = create_response.json()["id"]

    response = client.put(
        f"/documents/{doc_id}",
        json={"title": "Updated", "content": "Updated content"},
    )

    assert response.status_code == 422


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
    assert data["error"]["code"] == "ILLEGAL_TRANSITION"


def test_approve_draft_returns_400_illegal_transition() -> None:
    """Test approving a draft document returns 400 illegal transition."""
    app = create_app()
    client = TestClient(app)
    create_response = client.post(
        "/documents",
        json={"title": "Test", "content": "Body"},
    )
    doc_id = create_response.json()["id"]

    conflict_response = client.post(
        f"/documents/{doc_id}/approve",
        headers={"If-Match": "0"},
    )

    assert conflict_response.status_code == 400
    data = conflict_response.json()
    assert "error" in data
    assert data["error"]["code"] == "ILLEGAL_TRANSITION"


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
    """Test repository isolation across app instances."""
    app1 = create_app()
    client1 = TestClient(app1)

    app2 = create_app()
    client2 = TestClient(app2)

    response = client1.post(
        "/documents",
        json={"title": "A", "content": "B"},
    )
    doc_id = response.json()["id"]

    response2 = client2.get(f"/documents/{doc_id}")

    assert response2.status_code == 404


def test_health_endpoint_returns_ok() -> None:
    """Test /health/live returns ok status."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_endpoint_returns_ready(monkeypatch: MonkeyPatch) -> None:
    """Test /health/ready returns ready when database is available."""

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
            _ = statement

    def fake_get_session_factory() -> Callable[[], DummySession]:
        return lambda: DummySession()

    monkeypatch.setattr("api.app.get_session_factory", fake_get_session_factory)
    app = create_app()
    client = TestClient(app)

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_readiness_endpoint_returns_503_on_failure(
    monkeypatch: MonkeyPatch,
) -> None:
    """Test /health/ready returns 503 when database is unavailable."""

    def fake_get_session_factory() -> Callable[[], object]:
        raise RuntimeError("db down")

    monkeypatch.setattr("api.app.get_session_factory", fake_get_session_factory)
    app = create_app()
    client = TestClient(app)

    response = client.get("/health/ready")

    assert response.status_code == 503
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "SERVICE_UNAVAILABLE"


def test_request_id_appears_in_logs(capsys: pytest.CaptureFixture[str]) -> None:
    """Test that every request gets a unique request_id logged."""
    app = create_app()
    client = TestClient(app)
    
    response = client.post(
        "/documents",
        json={"title": "Test", "content": "Body"},
    )
    
    assert response.status_code == 201
    
    # Capture stdout/stderr
    captured = capsys.readouterr()
    
    # Verify request_id appears in log output
    assert "request_id" in captured.out, f"No request_id found in logs:\n{captured.out}"
