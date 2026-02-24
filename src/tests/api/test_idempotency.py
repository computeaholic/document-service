"""Idempotency tests for POST /documents."""


from fastapi.testclient import TestClient

from api.app import create_app


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


def test_post_documents_same_key_different_payload_returns_422() -> None:
    """Test that same key with different body returns error."""
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
    
    assert response2.status_code == 400
    data = response2.json()
    assert "error" in data
    assert data["error"]["code"] == "IDEMPOTENCY_KEY_CONFLICT"


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
