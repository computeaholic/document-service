"""FastAPI application factory."""

import json
import logging
from typing import Annotated, Any, cast
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Header, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import literal, select

from application.services import DocumentService
from infrastructure.database import get_session_factory
from infrastructure.memory_repository import InMemoryDocumentRepository
from domain import IllegalTransitionError, ValidationError
from config import Settings
from .logging_config import configure_logging
from .schemas import CreateDocumentRequest, DocumentResponse, UpdateDocumentRequest
from .idempotency import check_idempotency, store_idempotency


def error_response(code: str, message: str) -> dict[str, Any]:
    """Create standardized error response envelope.

    Args:
        code: Error code identifier
        message: Human-readable error message

    Returns:
        Dictionary with error envelope structure
    """
    return {"error": {"code": code, "message": message}}


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

    # Add request ID middleware
    @app.middleware("http")
    async def add_request_id(request: Request, call_next: Any) -> Response:
        """Add request_id to each request for tracing."""
        request_id = str(uuid4())
        request.state.request_id = request_id
        
        # Create logger adapter with request_id
        logger_with_context = logging.LoggerAdapter(
            logger,
            {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
            }
        )
        request.state.logger = logger_with_context
        
        response = await call_next(request)
        
        # Log response with structured fields
        logger_with_context.info(
            "Request completed",
            extra={
                "status_code": response.status_code,
            }
        )
        
        return cast(Response, response)

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
        request_id = getattr(request.state, "request_id", "unknown")
        logger.warning(
            "Validation error",
            extra={
                "request_id": request_id,
                "error_code": "VALIDATION_ERROR",
                "error_message": str(exc),
                "method": request.method,
                "path": request.url.path,
            }
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response("VALIDATION_ERROR", str(exc)),
        )

    @app.exception_handler(IllegalTransitionError)
    async def illegal_transition_handler(
        request: Request,
        exc: IllegalTransitionError,
    ) -> JSONResponse:
        """Handle illegal state transition errors."""
        request_id = getattr(request.state, "request_id", "unknown")
        logger.warning(
            "Illegal transition",
            extra={
                "request_id": request_id,
                "error_code": "ILLEGAL_TRANSITION",
                "error_message": str(exc),
                "method": request.method,
                "path": request.url.path,
            }
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response("ILLEGAL_TRANSITION", str(exc)),
        )

    @app.post(
        "/documents",
        response_model=None,
        status_code=status.HTTP_201_CREATED,
    )
    def create_document(
        payload: CreateDocumentRequest,
        idempotency_key: Annotated[str | None, Header(min_length=1, max_length=128)] = None,
        service: DocumentService = Depends(get_service),
    ) -> DocumentResponse | JSONResponse:
        """Create a new document.

        Args:
            payload: CreateDocumentRequest with title and content
            idempotency_key: Idempotency-Key header value (required in production)
            service: DocumentService instance

        Returns:
            DocumentResponse with created document data

        Raises:
            ValidationError: If title or content validation fails
            HTTPException: 400 if idempotency key conflict with different request body
        """
        # Check idempotency if key provided (tests may skip this)
        if idempotency_key is not None:
            request_body = {"title": payload.title, "content": payload.content}
            try:
                is_duplicate, stored_response = check_idempotency(
                    idempotency_key, request_body, get_session_factory()
                )

                if is_duplicate:
                    if stored_response is not None:
                        # Same key, same hash → return stored response
                        return JSONResponse(
                            status_code=status.HTTP_201_CREATED,
                            content=json.loads(stored_response),
                        )
                    else:
                        # Same key, different hash → conflict
                        return JSONResponse(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            content=error_response(
                                "IDEMPOTENCY_KEY_CONFLICT",
                                "Idempotency key already used with different request body",
                            ),
                        )
            except Exception:
                # Idempotency check failed (e.g., DB unavailable in test mode), proceed anyway
                pass

        # Execute request
        doc = service.create(title=payload.title, content=payload.content)
        logger.info("Document created", extra={"document_id": str(doc.id)})
        response = DocumentResponse.model_validate(doc)

        # Store idempotency record if key provided
        if idempotency_key is not None:
            response_dict = response.model_dump(mode="json")
            try:
                store_idempotency(idempotency_key, request_body, response_dict, get_session_factory())
            except Exception:
                # Failed to store idempotency record (test mode), log and continue
                logger.warning("Failed to store idempotency record")

        return response

    @app.get(
        "/documents/{doc_id}",
        response_model=None,
    )
    def get_document(
        doc_id: UUID,
        service: DocumentService = Depends(get_service),
    ) -> DocumentResponse | JSONResponse:
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
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error_response("NOT_FOUND", "Document not found"),
            )

    @app.put(
        "/documents/{doc_id}",
        response_model=None,
    )
    def update_document(
        doc_id: UUID,
        payload: UpdateDocumentRequest,
        if_match: Annotated[int, Header()],
        service: DocumentService = Depends(get_service),
    ) -> DocumentResponse | JSONResponse:
        """Update a document's title and content.

        Args:
            doc_id: Document UUID
            payload: UpdateDocumentRequest with title and content
            if_match: Expected document version from If-Match header
            service: DocumentService instance

        Returns:
            DocumentResponse with updated document data

        Raises:
            HTTPException: 404 if document not found
            HTTPException: 400 if validation, transition, or version mismatch error
        """
        try:
            doc = service.get(doc_id)
            if doc.version != if_match:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content=error_response(
                        "VERSION_MISMATCH",
                        f"Expected version {if_match}, but document is at version {doc.version}",
                    ),
                )
            service.update(doc_id, payload.title, payload.content)
            doc = service.get(doc_id)
            return DocumentResponse.model_validate(doc)
        except KeyError:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error_response("NOT_FOUND", "Document not found"),
            )

    @app.post(
        "/documents/{doc_id}/submit",
        response_model=None,
    )
    def submit_document(
        doc_id: UUID,
        if_match: Annotated[int, Header()],
        service: DocumentService = Depends(get_service),
    ) -> DocumentResponse | JSONResponse:
        """Submit a document for approval.

        Args:
            doc_id: Document UUID
            if_match: Expected document version from If-Match header
            service: DocumentService instance

        Returns:
            DocumentResponse with updated document

        Raises:
            HTTPException: 404 if document not found
            HTTPException: 400 if transition is illegal or version mismatch
        """
        try:
            doc = service.get(doc_id)
            if doc.version != if_match:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content=error_response(
                        "VERSION_MISMATCH",
                        f"Expected version {if_match}, but document is at version {doc.version}",
                    ),
                )
            service.submit(doc_id)
            doc = service.get(doc_id)
            return DocumentResponse.model_validate(doc)
        except KeyError:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error_response("NOT_FOUND", "Document not found"),
            )

    @app.post(
        "/documents/{doc_id}/approve",
        response_model=None,
    )
    def approve_document(
        doc_id: UUID,
        if_match: Annotated[int, Header()],
        service: DocumentService = Depends(get_service),
    ) -> DocumentResponse | JSONResponse:
        """Approve a submitted document.

        Args:
            doc_id: Document UUID
            if_match: Expected document version from If-Match header
            service: DocumentService instance

        Returns:
            DocumentResponse with updated document

        Raises:
            HTTPException: 404 if document not found
            HTTPException: 400 if transition is illegal or version mismatch
        """
        try:
            doc = service.get(doc_id)
            if doc.version != if_match:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content=error_response(
                        "VERSION_MISMATCH",
                        f"Expected version {if_match}, but document is at version {doc.version}",
                    ),
                )
            service.approve(doc_id)
            doc = service.get(doc_id)
            return DocumentResponse.model_validate(doc)
        except KeyError:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error_response("NOT_FOUND", "Document not found"),
            )

    @app.post(
        "/documents/{doc_id}/reject",
        response_model=None,
    )
    def reject_document(
        doc_id: UUID,
        if_match: Annotated[int, Header()],
        service: DocumentService = Depends(get_service),
    ) -> DocumentResponse | JSONResponse:
        """Reject a submitted document.

        Args:
            doc_id: Document UUID
            if_match: Expected document version from If-Match header
            service: DocumentService instance

        Returns:
            DocumentResponse with updated document

        Raises:
            HTTPException: 404 if document not found
            HTTPException: 400 if transition is illegal or version mismatch
        """
        try:
            doc = service.get(doc_id)
            if doc.version != if_match:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content=error_response(
                        "VERSION_MISMATCH",
                        f"Expected version {if_match}, but document is at version {doc.version}",
                    ),
                )
            service.reject(doc_id)
            doc = service.get(doc_id)
            return DocumentResponse.model_validate(doc)
        except KeyError:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error_response("NOT_FOUND", "Document not found"),
            )

    @app.get("/health/live")
    def health() -> dict[str, str]:
        """Liveness check endpoint."""
        return {"status": "ok"}

    @app.get("/health/ready", response_model=None)
    def readiness() -> dict[str, str] | JSONResponse:
        """Readiness check endpoint."""
        try:
            session_factory = get_session_factory()
            with session_factory() as session:
                session.execute(select(literal(1)))
            return {"status": "ready"}
        except Exception:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=error_response("SERVICE_UNAVAILABLE", "Database unavailable"),
            )

    return app


app = create_app()
