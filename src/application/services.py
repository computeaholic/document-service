"""Document service application layer.

Orchestrates document use cases without business logic duplication.
"""

from typing import Iterable
from uuid import UUID

from application.repositories import DocumentRepository
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
        self.get(doc_id).update(title, content)

    def submit(self, doc_id: UUID) -> None:
        """Submit a document for approval.

        Args:
            doc_id: Document UUID

        Raises:
            KeyError: If document not found
            IllegalTransitionError: If submit not allowed in current state
            ValidationError: If content is empty
        """
        self.get(doc_id).submit()

    def approve(self, doc_id: UUID) -> None:
        """Approve a submitted document.

        Args:
            doc_id: Document UUID

        Raises:
            KeyError: If document not found
            IllegalTransitionError: If approve not allowed in current state
        """
        self.get(doc_id).approve()

    def reject(self, doc_id: UUID) -> None:
        """Reject a submitted document.

        Args:
            doc_id: Document UUID

        Raises:
            KeyError: If document not found
            IllegalTransitionError: If reject not allowed in current state
        """
        self.get(doc_id).reject()

    def list(self) -> Iterable[Document]:
        """List all documents in the repository.

        Returns:
            Iterable of all documents
        """
        return self._repository.list()
