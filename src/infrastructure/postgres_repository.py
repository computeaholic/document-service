"""Postgres-backed document repository implementation."""

from datetime import datetime, timezone
from typing import Iterable
from uuid import UUID

from sqlalchemy import select, update
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

        Note:
            For updates, this method enforces optimistic concurrency at the
            database level by checking version in the WHERE clause. This provides
            defense-in-depth alongside application-layer version validation.
        """
        with self._session_factory() as session:
            with session.begin():
                existing = session.get(DocumentModel, document.id)
                if existing is not None:
                    # Update existing document with version check
                    # Defense-in-depth: Application layer already validated version,
                    # but we enforce it at DB level to prevent race conditions
                    expected_version = document.version - 1

                    result = session.execute(
                        update(DocumentModel)
                        .where(DocumentModel.id == document.id)
                        .where(DocumentModel.version == expected_version)
                        .values(
                            title=document.title,
                            content=document.content,
                            status=document.status.value,
                            version=document.version,
                            updated_at=document.updated_at,
                        )
                    )

                    if result.rowcount == 0:
                        # Version mismatch or document disappeared
                        # Application layer should have caught this, but defensive check
                        raise ValueError(
                            f"Concurrent modification detected for document {document.id}"
                        )
                else:
                    # Create new document
                    model = DocumentModel(
                        id=document.id,
                        title=document.title,
                        content=document.content,
                        status=document.status.value,
                        version=document.version,
                        created_at=document.created_at,
                        updated_at=document.updated_at,
                    )
                    session.add(model)

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
        doc = object.__new__(Document)
        doc.id = model.id
        doc.title = model.title
        doc.content = model.content
        doc.status = Status(model.status)
        doc.version = model.version
        doc.created_at = model.created_at
        doc.updated_at = model.updated_at
        doc.clock = lambda: datetime.now(timezone.utc)
        return doc
