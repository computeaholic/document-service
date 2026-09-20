"""Postgres-backed document repository implementation."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Iterable
from uuid import UUID
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from application.repositories import DocumentRepository, IdempotentCreateResult
from domain import Document, Status, VersionConflictError
from infrastructure.models import DocumentModel, IdempotencyKeyModel


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
                        raise VersionConflictError(
                            f"Concurrent modification detected for document {document.id}"
                        )
                else:
                    # Create new document
                    self._persist_document_model(session, document)

    def create_idempotent(
        self,
        idempotency_key: str,
        title: str,
        content: str,
    ) -> IdempotentCreateResult:
        request_hash = self._get_request_hash({"title": title, "content": content})

        try:
            with self._session_factory() as session, session.begin():
                existing = self._load_idempotency_record(session, idempotency_key)
                if existing is not None:
                    return self._resolve_existing_record(
                        session, existing, request_hash
                    )

                document = Document(title=title, content=content)
                self._persist_document_model(session, document)
                self._persist_idempotency_record(
                    session,
                    idempotency_key,
                    request_hash,
                    document,
                )
                return IdempotentCreateResult(outcome="created", document=document)
        except IntegrityError as exc:
            return self._resolve_conflicted_create(idempotency_key, request_hash, exc)

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

    def _persist_document_model(self, session: Session, document: Document) -> None:
        session.add(
            DocumentModel(
                id=document.id,
                title=document.title,
                content=document.content,
                status=document.status.value,
                version=document.version,
                created_at=document.created_at,
                updated_at=document.updated_at,
            )
        )

    def _load_idempotency_record(
        self,
        session: Session,
        idempotency_key: str,
    ) -> IdempotencyKeyModel | None:
        return session.execute(
            select(IdempotencyKeyModel).where(
                IdempotencyKeyModel.key == idempotency_key
            )
        ).scalar_one_or_none()

    def _get_request_hash(self, request_body: dict[str, str]) -> str:
        body_json = json.dumps(request_body, sort_keys=True)
        return hashlib.sha256(body_json.encode()).hexdigest()

    def _document_to_response_body(self, document: Document) -> dict[str, str | int]:
        return {
            "id": str(document.id),
            "title": document.title,
            "content": document.content,
            "status": document.status.value,
            "version": document.version,
            "created_at": document.created_at.isoformat().replace("+00:00", "Z"),
            "updated_at": document.updated_at.isoformat().replace("+00:00", "Z"),
        }

    def _persist_idempotency_record(
        self,
        session: Session,
        idempotency_key: str,
        request_hash: str,
        document: Document,
    ) -> None:
        session.add(
            IdempotencyKeyModel(
                id=uuid4(),
                key=idempotency_key,
                request_hash=request_hash,
                response_body=json.dumps(self._document_to_response_body(document)),
            )
        )

    def _load_document_from_idempotency_record(
        self,
        session: Session,
        record: IdempotencyKeyModel,
    ) -> Document:
        response_body = json.loads(record.response_body)
        document_id = UUID(str(response_body["id"]))
        model = session.get(DocumentModel, document_id)
        if model is None:
            raise IntegrityError(
                "missing document for idempotency record",
                {},
                Exception("missing document for idempotency record"),
            )
        return self._to_domain(model)

    def _resolve_existing_record(
        self,
        session: Session,
        record: IdempotencyKeyModel,
        request_hash: str,
    ) -> IdempotentCreateResult:
        if record.request_hash != request_hash:
            return IdempotentCreateResult(outcome="conflict")
        return IdempotentCreateResult(
            outcome="replayed",
            document=self._load_document_from_idempotency_record(session, record),
        )

    def _resolve_conflicted_create(
        self,
        idempotency_key: str,
        request_hash: str,
        original_error: IntegrityError,
    ) -> IdempotentCreateResult:
        with self._session_factory() as session:
            existing = self._load_idempotency_record(session, idempotency_key)
            if existing is None:
                raise original_error
            return self._resolve_existing_record(session, existing, request_hash)
