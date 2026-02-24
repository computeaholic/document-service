"""Postgres integration tests for persistence validation."""

from collections.abc import Generator
import os
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

from api.app import create_app
from infrastructure.models import DocumentModel

pytestmark = pytest.mark.integration


@pytest.fixture
def postgres_url() -> str:
    """Get Postgres URL from environment or use default."""
    return os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+psycopg://test:test@localhost:5433/document_service_test",
    )


@pytest.fixture
def postgres_engine(postgres_url: str) -> Generator[Engine, None, None]:
    """Create Postgres engine for tests."""
    engine = create_engine(postgres_url)
    yield engine
    engine.dispose()


@pytest.fixture
def postgres_session_factory(postgres_engine: Engine) -> sessionmaker[Session]:
    """Create session factory for tests."""
    return sessionmaker(bind=postgres_engine)


def test_postgres_persists_created_and_updated_timestamps(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """Test that Postgres correctly persists timestamps."""
    app = create_app()
    client = TestClient(app)

    # Create document
    response = client.post(
        "/documents",
        json={"title": "Timestamp Test", "content": "Testing timestamps"},
        headers={"Idempotency-Key": "pg-ts-1"},
    )
    assert response.status_code == 201
    doc_id = response.json()["id"]

    # Retrieve from database directly
    with postgres_session_factory() as session:
        doc_model = session.get(DocumentModel, doc_id)
        assert doc_model is not None

        # Verify timestamps exist
        assert doc_model.created_at is not None
        assert doc_model.updated_at is not None

        # Store original timestamps
        original_created = doc_model.created_at
        original_updated = doc_model.updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.1)

    # Update document
    get_response = client.get(f"/documents/{doc_id}")
    version = get_response.json()["version"]

    update_response = client.put(
        f"/documents/{doc_id}",
        json={
            "title": "Updated Title",
            "content": "Updated Content",
        },
        headers={"If-Match": str(version)},
    )
    assert update_response.status_code == 200

    # Verify timestamps updated
    with postgres_session_factory() as session:
        doc_model = session.get(DocumentModel, doc_id)
        assert doc_model is not None

        # created_at should remain unchanged
        assert doc_model.created_at == original_created

        # updated_at should be newer
        assert doc_model.updated_at > original_updated


def test_version_increment_occurs_only_once_per_successful_update(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """Test that version increments exactly once per successful update."""
    app = create_app()
    client = TestClient(app)

    idempotency_key = "version-test-key"

    # Create document
    create_response = client.post(
        "/documents",
        json={"title": "Version Test", "content": "Testing version"},
        headers={"Idempotency-Key": idempotency_key},
    )
    assert create_response.status_code == 201
    doc_id = create_response.json()["id"]
    initial_version = create_response.json()["version"]
    assert initial_version == 0

    # Replay idempotent create
    replay_response = client.post(
        "/documents",
        json={"title": "Version Test", "content": "Testing version"},
        headers={"Idempotency-Key": idempotency_key},
    )
    assert replay_response.status_code == 201
    replayed_version = replay_response.json()["version"]

    # Version should not increment on replay
    assert replayed_version == initial_version

    # Now perform actual update
    update_response = client.put(
        f"/documents/{doc_id}",
        json={
            "title": "Updated",
            "content": "Updated content",
        },
        headers={"If-Match": str(initial_version)},
    )
    assert update_response.status_code == 200
    updated_version = update_response.json()["version"]

    # Version should increment exactly once
    assert updated_version == initial_version + 1

    # Verify in database
    with postgres_session_factory() as session:
        doc_model = session.get(DocumentModel, doc_id)
        assert doc_model is not None
        assert doc_model.version == updated_version


def test_postgres_handles_concurrent_updates_with_version_check(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """Test that concurrent updates are rejected via version check."""
    app = create_app()
    client = TestClient(app)

    # Create document
    response = client.post(
        "/documents",
        json={"title": "Concurrency Test", "content": "Test content"},
        headers={"Idempotency-Key": "pg-concurrency-1"},
    )
    assert response.status_code == 201
    doc_id = response.json()["id"]
    version = response.json()["version"]

    # First update succeeds
    update1 = client.put(
        f"/documents/{doc_id}",
        json={"title": "Update 1", "content": "Content 1"},
        headers={"If-Match": str(version)},
    )
    assert update1.status_code == 200
    new_version = update1.json()["version"]
    assert new_version == version + 1

    # Second update with stale version fails
    update2 = client.put(
        f"/documents/{doc_id}",
        json={"title": "Update 2", "content": "Content 2"},
        headers={"If-Match": str(version)},  # Using old version
    )
    assert update2.status_code == 409
    data = update2.json()
    assert "error" in data
    assert data["error"]["code"] == "version_conflict"
