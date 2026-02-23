"""FastAPI application factory."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import literal, select

from application.services import DocumentService
from infrastructure.database import get_session_factory
from infrastructure.memory_repository import InMemoryDocumentRepository
from domain import IllegalTransitionError, ValidationError
from config import Settings
from .logging_config import configure_logging
from .schemas import CreateDocumentRequest, DocumentResponse


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    configure_logging()
    logger = logging.getLogger("document_service")
    settings = Settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Create repository once at app startup for consistent state
    repository = InMemoryDocumentRepository()

    def get_repository() -> InMemoryDocumentRepository:
        """Provide InMemoryDocumentRepository (same instance per app)."""
        return repository

    def get_service(
        repository: Annotated[InMemoryDocumentRepository, Depends(get_repository)],
    ) -> DocumentService:
        """Provide DocumentService with injected repository."""
        return DocumentService(repository)

    @app.exception_handler(ValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: ValidationError,
    ) -> JSONResponse:
        """Handle validation errors."""
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )

    @app.exception_handler(IllegalTransitionError)
    async def illegal_transition_handler(
        request: Request,
        exc: IllegalTransitionError,
    ) -> JSONResponse:
        """Handle illegal state transition errors."""
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": str(exc)},
        )

    @app.post(
        "/documents",
        response_model=DocumentResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_document(
        payload: CreateDocumentRequest,
        service: DocumentService = Depends(get_service),
    ) -> DocumentResponse:
        """Create a new document.

        Args:
            payload: CreateDocumentRequest with title and content
            service: DocumentService instance

        Returns:
            DocumentResponse with created document data

        Raises:
            ValidationError: If title or content validation fails
        """
        doc = service.create(title=payload.title, content=payload.content)
        logger.info("Document created", extra={"document_id": str(doc.id)})
        return DocumentResponse.model_validate(doc)

    @app.get(
        "/documents/{doc_id}",
        response_model=DocumentResponse,
    )
    def get_document(
        doc_id: UUID,
        service: DocumentService = Depends(get_service),
    ) -> DocumentResponse:
        """Retrieve a document by ID.

        Args:
            doc_id: Document UUID
            service: DocumentService instance

        Returns:
            DocumentResponse with document data

        Raises:
            HTTPException: 404 if document not found
        """
        try:
            doc = service.get(doc_id)
            return DocumentResponse.model_validate(doc)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

    @app.post(
        "/documents/{doc_id}/submit",
        response_model=DocumentResponse,
    )
    def submit_document(
        doc_id: UUID,
        service: DocumentService = Depends(get_service),
    ) -> DocumentResponse:
        """Submit a document for approval.

        Args:
            doc_id: Document UUID
            service: DocumentService instance

        Returns:
            DocumentResponse with updated document

        Raises:
            HTTPException: 404 if document not found
            HTTPException: 409 if transition is illegal
        """
        try:
            service.submit(doc_id)
            doc = service.get(doc_id)
            return DocumentResponse.model_validate(doc)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

    @app.post(
        "/documents/{doc_id}/approve",
        response_model=DocumentResponse,
    )
    def approve_document(
        doc_id: UUID,
        service: DocumentService = Depends(get_service),
    ) -> DocumentResponse:
        """Approve a submitted document.

        Args:
            doc_id: Document UUID
            service: DocumentService instance

        Returns:
            DocumentResponse with updated document

        Raises:
            HTTPException: 404 if document not found
            HTTPException: 409 if transition is illegal
        """
        try:
            service.approve(doc_id)
            doc = service.get(doc_id)
            return DocumentResponse.model_validate(doc)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

    @app.post(
        "/documents/{doc_id}/reject",
        response_model=DocumentResponse,
    )
    def reject_document(
        doc_id: UUID,
        service: DocumentService = Depends(get_service),
    ) -> DocumentResponse:
        """Reject a submitted document.

        Args:
            doc_id: Document UUID
            service: DocumentService instance

        Returns:
            DocumentResponse with updated document

        Raises:
            HTTPException: 404 if document not found
            HTTPException: 409 if transition is illegal
        """
        try:
            service.reject(doc_id)
            doc = service.get(doc_id)
            return DocumentResponse.model_validate(doc)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

    @app.get("/health")
    def health() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "ok"}

    @app.get("/ready")
    def readiness() -> dict[str, str]:
        """Readiness check endpoint."""
        try:
            session_factory = get_session_factory()
            with session_factory() as session:
                session.execute(select(literal(1)))
            return {"status": "ready"}
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database unavailable",
            )

    return app


app = create_app()
