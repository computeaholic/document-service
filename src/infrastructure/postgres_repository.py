"""Postgres-backed document repository implementation."""

from typing import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from application.repositories import DocumentRepository
from domain import Document, Status
from infrastructure.models import DocumentModel


class PostgresDocumentRepository(DocumentRepository):
    """Postgres repository for Document persistence."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        """Initialize repository with a session factory.

        Args:
            session_factory: SQLAlchemy session factory
        """
        self._session_factory = session_factory

    def add(self, document: Document) -> None:
        """Add a document to the repository.

        Args:
            document: Document to add
        """
        model = DocumentModel(
            id=document.id,
            title=document.title,
            content=document.content,
            status=document.status.value,
            version=document.version,
        )
        with self._session_factory() as session:
            existing = session.get(DocumentModel, document.id)
            if existing is not None:
                existing.title = document.title
                existing.content = document.content
                existing.status = document.status.value
                existing.version = document.version
            else:
                session.add(model)
            session.commit()

    def get(self, doc_id: UUID) -> Document:
        """Retrieve a document by ID.

        Args:
            doc_id: Document UUID

        Returns:
            Document

        Raises:
            KeyError: If document not found
        """
        with self._session_factory() as session:
            model = session.get(DocumentModel, doc_id)
            if model is None:
                raise KeyError(doc_id)
            return self._to_domain(model)

    def list(self) -> Iterable[Document]:
        """List all documents.

        Returns:
            Iterable of all documents
        """
        with self._session_factory() as session:
            models = session.execute(select(DocumentModel)).scalars().all()
            return [self._to_domain(model) for model in models]

    def _to_domain(self, model: DocumentModel) -> Document:
        """Convert a persistence model to a domain document.

        Args:
            model: DocumentModel instance

        Returns:
            Document
        """
        return Document(
            id=model.id,
            title=model.title,
            content=model.content,
            status=Status(model.status),
            version=model.version,
        )
