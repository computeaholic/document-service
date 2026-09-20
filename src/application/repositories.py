"""Repository abstraction for Document persistence."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable
from typing import Literal
from uuid import UUID

from domain import Document


@dataclass(frozen=True)
class IdempotentCreateResult:
    """Result of an idempotent create attempt."""

    outcome: Literal["created", "replayed", "conflict"]
    document: Document | None = None


class DocumentRepository(ABC):
    """Abstract repository for Document persistence."""

    @abstractmethod
    def add(self, document: Document) -> None:
        """Add a document to the repository.

        Args:
            document: Document to add
        """

    @abstractmethod
    def create_idempotent(
        self,
        idempotency_key: str,
        title: str,
        content: str,
    ) -> IdempotentCreateResult:
        """Atomically create or replay a document for an idempotency key."""

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
