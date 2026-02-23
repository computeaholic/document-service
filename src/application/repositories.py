"""Repository abstraction for Document persistence."""

from abc import ABC, abstractmethod
from typing import Iterable
from uuid import UUID

from domain import Document


class DocumentRepository(ABC):
    """Abstract repository for Document persistence."""

    @abstractmethod
    def add(self, document: Document) -> None:
        """Add a document to the repository.

        Args:
            document: Document to add
        """

    @abstractmethod
    def get(self, doc_id: UUID) -> Document:
        """Retrieve a document by ID.

        Args:
            doc_id: Document UUID

        Returns:
            Document

        Raises:
            KeyError: If document not found
        """

    @abstractmethod
    def list(self) -> Iterable[Document]:
        """List all documents.

        Returns:
            Iterable of all documents
        """
