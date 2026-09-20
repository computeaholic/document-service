"""Idempotency tests for POST /documents."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from api.app import create_app
from infrastructure.database import get_session_factory
from infrastructure.postgres_repository import PostgresDocumentRepository
from infrastructure.models import DocumentModel, IdempotencyKeyModel


def _post_document(
    app: FastAPI,
    idempotency_key: str,
    payload: dict[str, str],
) -> tuple[int, dict[str, Any]]:
    with TestClient(app) as client:
        response = client.post(
            "/documents",
            json=payload,
            headers={"Idempotency-Key": idempotency_key},
        )
    return response.status_code, response.json()


def test_post_documents_replays_same_response_with_same_idempotency_key() -> None:
    """Test that same idempotency key returns cached response."""
    app = create_app()
    client = TestClient(app)

    idempotency_key = "test-key-replay-123"
    payload = {"title": "Test Document", "content": "Test Content"}

    # First request
    response1 = client.post(
        "/documents",
        json=payload,
        headers={"Idempotency-Key": idempotency_key},
    )

    assert response1.status_code == 201
    data1 = response1.json()
    version1 = data1["version"]
    doc_id1 = data1["id"]

    # Second request with same key and body
    response2 = client.post(
        "/documents",
        json=payload,
        headers={"Idempotency-Key": idempotency_key},
    )

    assert response2.status_code == 201
    data2 = response2.json()

    # Assert responses are identical
    assert data2["id"] == doc_id1
    assert data2["version"] == version1
    assert data2["title"] == payload["title"]
    assert data2["content"] == payload["content"]

    # Verify document was only created once
    get_response = client.get(f"/documents/{doc_id1}")
    assert get_response.status_code == 200


def test_post_documents_same_key_different_payload_returns_409() -> None:
    """Test that same key with different body returns conflict."""
    app = create_app()
    client = TestClient(app)

    idempotency_key = "test-key-conflict-456"

    # First request
    response1 = client.post(
        "/documents",
        json={"title": "First Title", "content": "First Content"},
        headers={"Idempotency-Key": idempotency_key},
    )

    assert response1.status_code == 201

    # Second request with same key but different body
    response2 = client.post(
        "/documents",
        json={"title": "Different Title", "content": "Different Content"},
        headers={"Idempotency-Key": idempotency_key},
    )

    assert response2.status_code == 409
    data = response2.json()
    assert "error" in data
    assert data["error"]["code"] == "idempotency_key_conflict"


def test_post_documents_different_keys_create_separate_documents() -> None:
    """Test that different idempotency keys create separate documents."""
    app = create_app()
    client = TestClient(app)

    payload = {"title": "Same Title", "content": "Same Content"}

    # Request with key 1
    response1 = client.post(
        "/documents",
        json=payload,
        headers={"Idempotency-Key": "key-1"},
    )
    assert response1.status_code == 201
    doc_id1 = response1.json()["id"]

    # Request with key 2 (same payload, different key)
    response2 = client.post(
        "/documents",
        json=payload,
        headers={"Idempotency-Key": "key-2"},
    )
    assert response2.status_code == 201
    doc_id2 = response2.json()["id"]

    # Should create two different documents
    assert doc_id1 != doc_id2


def test_post_documents_concurrent_same_key_same_payload_replays_single_result(
    monkeypatch: MonkeyPatch,
) -> None:
    """Concurrent first-use requests with the same key/body persist one document."""
    barrier = Barrier(2)
    original_load = PostgresDocumentRepository._load_idempotency_record
    idempotency_key = "concurrent-same-payload"
    payload = {"title": "Concurrent Doc", "content": "Same payload"}

    def synchronized_load(
        self: PostgresDocumentRepository,
        session: Session,
        key: str,
    ) -> object:
        record = original_load(self, session, key)
        if key == idempotency_key and record is None:
            barrier.wait(timeout=5)
        return record

    monkeypatch.setattr(
        PostgresDocumentRepository,
        "_load_idempotency_record",
        synchronized_load,
    )

    app = create_app()
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda _: _post_document(app, idempotency_key, payload),
                range(2),
            )
        )

    assert [status for status, _ in results] == [201, 201]
    first_body = results[0][1]
    second_body = results[1][1]
    assert first_body["id"] == second_body["id"]

    session_factory = get_session_factory()
    with session_factory() as session:
        assert (
            session.execute(
                select(func.count()).select_from(DocumentModel)
            ).scalar_one()
            == 1
        )
        assert (
            session.execute(
                select(func.count()).select_from(IdempotencyKeyModel)
            ).scalar_one()
            == 1
        )


def test_post_documents_concurrent_same_key_different_payload_persists_one_winner(
    monkeypatch: MonkeyPatch,
) -> None:
    """Concurrent first-use requests with the same key but different bodies do not double-create."""
    barrier = Barrier(2)
    original_load = PostgresDocumentRepository._load_idempotency_record
    idempotency_key = "concurrent-different-payload"
    payloads = [
        {"title": "Winner A", "content": "A"},
        {"title": "Winner B", "content": "B"},
    ]

    def synchronized_load(
        self: PostgresDocumentRepository,
        session: Session,
        key: str,
    ) -> object:
        record = original_load(self, session, key)
        if key == idempotency_key and record is None:
            barrier.wait(timeout=5)
        return record

    monkeypatch.setattr(
        PostgresDocumentRepository,
        "_load_idempotency_record",
        synchronized_load,
    )

    app = create_app()
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda payload: _post_document(app, idempotency_key, payload),
                payloads,
            )
        )

    statuses = sorted(status for status, _ in results)
    assert statuses == [201, 409]
    winner = next(body for status, body in results if status == 201)
    loser = next(body for status, body in results if status == 409)
    assert loser["error"]["code"] == "idempotency_key_conflict"

    session_factory = get_session_factory()
    with session_factory() as session:
        assert (
            session.execute(
                select(func.count()).select_from(DocumentModel)
            ).scalar_one()
            == 1
        )
        assert (
            session.execute(
                select(func.count()).select_from(IdempotencyKeyModel)
            ).scalar_one()
            == 1
        )
        persisted = session.execute(select(DocumentModel)).scalar_one()
        assert persisted.title == winner["title"]


def test_post_documents_idempotency_lookup_failure_fails_closed(
    monkeypatch: MonkeyPatch,
) -> None:
    """Lookup failures must not proceed without idempotency coordination."""

    def broken_lookup(*args: object, **kwargs: object) -> object:
        raise OperationalError("SELECT", {}, Exception("db down"))

    monkeypatch.setattr(
        PostgresDocumentRepository,
        "_load_idempotency_record",
        broken_lookup,
    )
    app = create_app()
    client = TestClient(app)

    response = client.post(
        "/documents",
        json={"title": "Lookup Failure", "content": "Body"},
        headers={"Idempotency-Key": "lookup-failure"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "db_unavailable"

    session_factory = get_session_factory()
    with session_factory() as session:
        assert (
            session.execute(
                select(func.count()).select_from(DocumentModel)
            ).scalar_one()
            == 0
        )
        assert (
            session.execute(
                select(func.count()).select_from(IdempotencyKeyModel)
            ).scalar_one()
            == 0
        )


def test_post_documents_idempotency_write_failure_rolls_back_document(
    monkeypatch: MonkeyPatch,
) -> None:
    """Write failures must not commit an orphan document."""

    def broken_persist(*args: object, **kwargs: object) -> None:
        raise OperationalError("INSERT", {}, Exception("db down"))

    monkeypatch.setattr(
        PostgresDocumentRepository,
        "_persist_idempotency_record",
        broken_persist,
    )
    app = create_app()
    client = TestClient(app)

    response = client.post(
        "/documents",
        json={"title": "Write Failure", "content": "Body"},
        headers={"Idempotency-Key": "write-failure"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "db_unavailable"

    session_factory = get_session_factory()
    with session_factory() as session:
        assert (
            session.execute(
                select(func.count()).select_from(DocumentModel)
            ).scalar_one()
            == 0
        )
        assert (
            session.execute(
                select(func.count()).select_from(IdempotencyKeyModel)
            ).scalar_one()
            == 0
        )
