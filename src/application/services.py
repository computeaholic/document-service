"""Document service application layer.

Orchestrates document use cases without business logic duplication.
"""

from application.repositories import DocumentRepository, IdempotentCreateResult
from typing import Iterable
from uuid import UUID

from domain import Document


class DocumentService:
    """Application service for document operations.

    Orchestrates domain document operations with an injected repository.
    No business logic duplication.
    """

    def __init__(self, repository: DocumentRepository) -> None:
        """Initialize service with a document repository.

        Args:
            repository: DocumentRepository instance for persistence
        """
        self._repository = repository

    def create(self, title: str, content: str) -> Document:
        """Create a new document.

        Args:
            title: Document title
            content: Document content

        Returns:
            Created Document

        Raises:
            ValidationError: If title or content validation fails
        """
        doc = Document(title=title, content=content)
        self._repository.add(doc)
        return doc

    def create_idempotent(
        self,
        idempotency_key: str,
        title: str,
        content: str,
    ) -> IdempotentCreateResult:
        """Atomically create or replay a document for an idempotency key."""
        return self._repository.create_idempotent(idempotency_key, title, content)

    def get(self, doc_id: UUID) -> Document:
        """Retrieve a document by ID.

        Args:
            doc_id: Document UUID

        Returns:
            Document

        Raises:
            KeyError: If document not found
        """
        return self._repository.get(doc_id)

    def update(self, doc_id: UUID, title: str, content: str) -> None:
        """Update a document's title and content.

        Args:
            doc_id: Document UUID
            title: New title
            content: New content

        Raises:
            KeyError: If document not found
            IllegalTransitionError: If update not allowed in current state
            ValidationError: If title or content validation fails
        """
        doc = self.get(doc_id)
        doc.update(title, content)
        self._repository.add(doc)

    def submit(self, doc_id: UUID) -> None:
        """Submit a document for approval.

        Args:
            doc_id: Document UUID

        Raises:
            KeyError: If document not found
            IllegalTransitionError: If submit not allowed in current state
            ValidationError: If content is empty
        """
        doc = self.get(doc_id)
        doc.submit()
        self._repository.add(doc)

    def approve(self, doc_id: UUID) -> None:
        """Approve a submitted document.

        Args:
            doc_id: Document UUID

        Raises:
            KeyError: If document not found
            IllegalTransitionError: If approve not allowed in current state
        """
        doc = self.get(doc_id)
        doc.approve()
        self._repository.add(doc)

    def reject(self, doc_id: UUID) -> None:
        """Reject a submitted document.

        Args:
            doc_id: Document UUID

        Raises:
            KeyError: If document not found
            IllegalTransitionError: If reject not allowed in current state
        """
        doc = self.get(doc_id)
        doc.reject()
        self._repository.add(doc)

    def list(self) -> Iterable[Document]:
        """List all documents in the repository.

        Returns:
            Iterable of all documents
        """
        return self._repository.list()
