"""Integration tests for PostgresDocumentRepository."""

import pytest
from sqlalchemy.orm import Session, sessionmaker

from domain import Document, Status
from infrastructure.database import Base, get_engine, get_session_factory
from infrastructure.postgres_repository import PostgresDocumentRepository


def _session_factory() -> sessionmaker[Session]:
    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return get_session_factory()


def test_add_and_get_document_round_trip() -> None:
    session_factory = _session_factory()
    repo = PostgresDocumentRepository(session_factory)
    doc = Document(title="Title", content="Content")

    repo.add(doc)
    fetched = repo.get(doc.id)

    assert fetched.id == doc.id
    assert fetched.title == doc.title
    assert fetched.content == doc.content
    assert fetched.status == Status.draft
    assert fetched.version == 0


def test_get_missing_document_raises_key_error() -> None:
    session_factory = _session_factory()
    repo = PostgresDocumentRepository(session_factory)
    doc = Document(title="Title", content="Content")

    with pytest.raises(KeyError):
        repo.get(doc.id)


def test_list_documents_returns_all() -> None:
    session_factory = _session_factory()
    repo = PostgresDocumentRepository(session_factory)
    doc1 = Document(title="One", content="A")
    doc2 = Document(title="Two", content="B")

    repo.add(doc1)
    repo.add(doc2)
    docs = list(repo.list())

    ids = {d.id for d in docs}
    assert doc1.id in ids
    assert doc2.id in ids
