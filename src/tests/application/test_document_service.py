"""Application layer tests for DocumentService."""

import pytest
from uuid import UUID

from application.services import DocumentService
from infrastructure.memory_repository import InMemoryDocumentRepository
from domain import Document, IllegalTransitionError, ValidationError, Status


def test_create_document_returns_document() -> None:
    """Test creating a document returns a Document instance."""
    repository = InMemoryDocumentRepository()
    service = DocumentService(repository)
    doc = service.create(title="Test", content="Body")

    assert isinstance(doc, Document)
    assert doc.title == "Test"
    assert doc.content == "Body"
    assert doc.status == Status.draft
    assert isinstance(doc.id, UUID)


def test_create_stores_document_in_service() -> None:
    """Test created document is stored in service."""
    repository = InMemoryDocumentRepository()
    service = DocumentService(repository)
    doc = service.create(title="Test", content="Body")

    retrieved = service.get(doc.id)
    assert retrieved.id == doc.id
    assert retrieved.title == "Test"


def test_get_nonexistent_document_raises_key_error() -> None:
    """Test retrieving nonexistent document raises KeyError."""
    repository = InMemoryDocumentRepository()
    service = DocumentService(repository)
    fake_id = UUID("00000000-0000-0000-0000-000000000000")

    with pytest.raises(KeyError):
        service.get(fake_id)


def test_update_via_service_increments_version() -> None:
    """Test that service.update increments document version."""
    repository = InMemoryDocumentRepository()
    service = DocumentService(repository)
    doc = service.create(title="Initial", content="Body")
    v0 = doc.version

    service.update(doc.id, "Updated", "Body2")

    updated = service.get(doc.id)
    assert updated.version == v0 + 1
    assert updated.title == "Updated"
    assert updated.content == "Body2"


def test_update_overwrites_single_field() -> None:
    """Test updating only title or content as needed."""
    repository = InMemoryDocumentRepository()
    service = DocumentService(repository)
    doc = service.create(title="T", content="C")

    service.update(doc.id, "T2", "C")
    updated = service.get(doc.id)
    assert updated.title == "T2"
    assert updated.content == "C"


def test_submit_via_service() -> None:
    """Test submit operation through service."""
    repository = InMemoryDocumentRepository()
    service = DocumentService(repository)
    doc = service.create(title="T", content="Body")
    v0 = doc.version

    service.submit(doc.id)

    submitted = service.get(doc.id)
    assert submitted.status == Status.submitted
    assert submitted.version == v0 + 1


def test_submit_then_approve_via_service() -> None:
    """Test submit + approve flow orchestration."""
    repository = InMemoryDocumentRepository()
    service = DocumentService(repository)
    doc = service.create(title="T", content="Body")
    v0 = doc.version

    service.submit(doc.id)
    submitted = service.get(doc.id)
    assert submitted.version == v0 + 1

    service.approve(doc.id)
    approved = service.get(doc.id)
    assert approved.status == Status.approved
    assert approved.version == v0 + 2


def test_submit_then_reject_via_service() -> None:
    """Test submit + reject flow orchestration."""
    repository = InMemoryDocumentRepository()
    service = DocumentService(repository)
    doc = service.create(title="T", content="Body")
    v0 = doc.version

    service.submit(doc.id)
    service.reject(doc.id)

    rejected = service.get(doc.id)
    assert rejected.status == Status.rejected
    assert rejected.version == v0 + 2


def test_illegal_transition_bubbles_up_from_service() -> None:
    """Test that domain exceptions bubble up from service methods."""
    repository = InMemoryDocumentRepository()
    service = DocumentService(repository)
    doc = service.create(title="T", content="Body")

    service.submit(doc.id)

    # Cannot submit twice
    with pytest.raises(IllegalTransitionError):
        service.submit(doc.id)

    # Cannot approve twice
    service.approve(doc.id)
    with pytest.raises(IllegalTransitionError):
        service.approve(doc.id)


def test_validation_error_bubbles_up_from_service() -> None:
    """Test that validation errors from domain bubble up."""
    repository = InMemoryDocumentRepository()
    service = DocumentService(repository)

    # Empty title
    with pytest.raises(ValidationError):
        service.create(title="   ", content="Body")


def test_update_validation_error_bubbles_up() -> None:
    """Test validation errors during update."""
    repository = InMemoryDocumentRepository()
    service = DocumentService(repository)
    doc = service.create(title="T", content="Body")

    with pytest.raises(ValidationError):
        service.update(doc.id, "   ", "Body")


def test_multiple_documents_isolated() -> None:
    """Test multiple documents are isolated in service."""
    repository = InMemoryDocumentRepository()
    service = DocumentService(repository)
    doc1 = service.create(title="Doc1", content="A")
    doc2 = service.create(title="Doc2", content="B")

    service.submit(doc1.id)

    retrieved1 = service.get(doc1.id)
    retrieved2 = service.get(doc2.id)

    assert retrieved1.status == Status.submitted
    assert retrieved2.status == Status.draft


def test_list_documents_returns_all() -> None:
    """Test list returns all documents in service."""
    repository = InMemoryDocumentRepository()
    service = DocumentService(repository)
    doc1 = service.create(title="Doc1", content="A")
    doc2 = service.create(title="Doc2", content="B")
    doc3 = service.create(title="Doc3", content="C")

    docs = list(service.list())

    assert len(docs) == 3
    ids = {d.id for d in docs}
    assert doc1.id in ids
    assert doc2.id in ids
    assert doc3.id in ids


def test_list_documents_empty_repository() -> None:
    """Test list returns empty iterable for empty repository."""
    repository = InMemoryDocumentRepository()
    service = DocumentService(repository)

    docs = list(service.list())

    assert len(docs) == 0
