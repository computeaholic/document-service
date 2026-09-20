"""In-memory document repository implementation."""

from typing import Dict, Iterable
from uuid import UUID

from application.repositories import DocumentRepository, IdempotentCreateResult
from domain import Document


class InMemoryDocumentRepository(DocumentRepository):
    """In-memory repository for Document persistence."""

    def __init__(self) -> None:
        """Initialize repository with empty store."""
        self._store: Dict[UUID, Document] = {}
        self._idempotency_index: dict[str, tuple[tuple[str, str], UUID]] = {}

    def add(self, document: Document) -> None:
        """Add a document to the repository.

        Args:
            document: Document to add
        """
        self._store[document.id] = document

    def create_idempotent(
        self,
        idempotency_key: str,
        title: str,
        content: str,
    ) -> IdempotentCreateResult:
        payload = (title, content)
        existing = self._idempotency_index.get(idempotency_key)
        if existing is not None:
            existing_payload, doc_id = existing
            if existing_payload != payload:
                return IdempotentCreateResult(outcome="conflict")
            return IdempotentCreateResult(
                outcome="replayed", document=self._store[doc_id]
            )

        document = Document(title=title, content=content)
        self._store[document.id] = document
        self._idempotency_index[idempotency_key] = (payload, document.id)
        return IdempotentCreateResult(outcome="created", document=document)

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
