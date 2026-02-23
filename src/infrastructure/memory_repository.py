"""In-memory document repository implementation."""

from typing import Dict, Iterable
from uuid import UUID

from application.repositories import DocumentRepository
from domain import Document


class InMemoryDocumentRepository(DocumentRepository):
    """In-memory repository for Document persistence."""

    def __init__(self) -> None:
        """Initialize repository with empty store."""
        self._store: Dict[UUID, Document] = {}

    def add(self, document: Document) -> None:
        """Add a document to the repository.

        Args:
            document: Document to add
        """
        self._store[document.id] = document

    def get(self, doc_id: UUID) -> Document:
        """Retrieve a document by ID.

        Args:
            doc_id: Document UUID

        Returns:
            Document

        Raises:
            KeyError: If document not found
        """
        return self._store[doc_id]

    def list(self) -> Iterable[Document]:
        """List all documents.

        Returns:
            Iterable of all documents
        """
        return self._store.values()
