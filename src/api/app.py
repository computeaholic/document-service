"""FastAPI application factory."""

import logging
from typing import Annotated, Any, cast
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Header, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from application.services import DocumentService
from domain import IllegalTransitionError, ValidationError, VersionConflictError
from infrastructure.database import get_session_factory
from infrastructure.models import DocumentModel, IdempotencyKeyModel
from infrastructure.postgres_repository import PostgresDocumentRepository
from config import Settings
from .logging_config import configure_logging
from .schemas import CreateDocumentRequest, DocumentResponse, UpdateDocumentRequest


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

        base_extra = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
        }
        request.state.log_extra = base_extra

        response = await call_next(request)

        # Log response completion with required fields
        logger.info(
            "Request completed",
            extra={
                **base_extra,
                "status_code": response.status_code,
            },
        )

        return cast(Response, response)

    # Create repository once at app startup for consistent state
    repository = PostgresDocumentRepository(get_session_factory())

    def get_repository() -> PostgresDocumentRepository:
        """Provide PostgresDocumentRepository (same instance per app)."""
        return repository

    def get_service(
        repository: Annotated[PostgresDocumentRepository, Depends(get_repository)],
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
        logger.info(
            "Validation error",
            extra={
                "request_id": request_id,
                "error_code": "validation_error",
                "error_message": str(exc),
                "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                "method": request.method,
                "path": request.url.path,
            },
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_response("validation_error", str(exc)),
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """Handle request validation errors from FastAPI/Pydantic."""
        request_id = getattr(request.state, "request_id", "unknown")
        logger.info(
            "Request validation error",
            extra={
                "request_id": request_id,
                "error_code": "validation_error",
                "error_message": str(exc),
                "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                "method": request.method,
                "path": request.url.path,
            },
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_response("validation_error", "Invalid request"),
        )

    @app.exception_handler(IllegalTransitionError)
    async def illegal_transition_handler(
        request: Request,
        exc: IllegalTransitionError,
    ) -> JSONResponse:
        """Handle illegal state transition errors."""
        request_id = getattr(request.state, "request_id", "unknown")
        logger.info(
            "Illegal transition",
            extra={
                "request_id": request_id,
                "error_code": "illegal_transition",
                "error_message": str(exc),
                "status_code": status.HTTP_400_BAD_REQUEST,
                "method": request.method,
                "path": request.url.path,
            },
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response("illegal_transition", str(exc)),
        )

    @app.exception_handler(VersionConflictError)
    async def version_conflict_handler(
        request: Request,
        exc: VersionConflictError,
    ) -> JSONResponse:
        """Handle optimistic concurrency conflicts detected at write time."""
        request_id = getattr(request.state, "request_id", "unknown")
        logger.info(
            "Version conflict",
            extra={
                "request_id": request_id,
                "error_code": "version_conflict",
                "error_message": str(exc),
                "status_code": status.HTTP_409_CONFLICT,
                "method": request.method,
                "path": request.url.path,
            },
        )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=error_response("version_conflict", str(exc)),
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(
        request: Request,
        exc: SQLAlchemyError,
    ) -> JSONResponse:
        """Handle database infrastructure failures."""
        request_id = getattr(request.state, "request_id", "unknown")
        logger.info(
            "Database unavailable",
            extra={
                "request_id": request_id,
                "error_code": "db_unavailable",
                "error_message": str(exc),
                "status_code": status.HTTP_503_SERVICE_UNAVAILABLE,
                "method": request.method,
                "path": request.url.path,
            },
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=error_response("db_unavailable", "Database unavailable"),
        )

    @app.post(
        "/documents",
        response_model=DocumentResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_document(
        request: Request,
        payload: CreateDocumentRequest,
        idempotency_key: Annotated[str, Header(min_length=1, max_length=128)],
        service: DocumentService = Depends(get_service),
    ) -> DocumentResponse | JSONResponse:
        """Create a new document.

        Args:
            idempotency_key: Idempotency-Key header value (required in production)

        Returns:
            Created or replayed document data
        """
        result = service.create_idempotent(
            idempotency_key=idempotency_key,
            title=payload.title,
            content=payload.content,
        )

        if result.outcome == "conflict":
            request_id = getattr(request.state, "request_id", "unknown")
            logger.info(
                "Idempotency key conflict",
                extra={
                    "request_id": request_id,
                    "error_code": "idempotency_key_conflict",
                    "status_code": status.HTTP_409_CONFLICT,
                    "method": request.method,
                    "path": request.url.path,
                },
            )
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content=error_response(
                    "idempotency_key_conflict",
                    "Idempotency key already used with different request body",
                ),
            )

        if result.document is None:
            raise RuntimeError("Idempotent create completed without a document")
        base_extra = getattr(request.state, "log_extra", {})
        if result.outcome == "created":
            logger.info(
                "Document created",
                extra={
                    **base_extra,
                    "status_code": status.HTTP_201_CREATED,
                    "document_id": str(result.document.id),
                },
            )

        return DocumentResponse.model_validate(result.document)

    @app.get(
        "/documents/{doc_id}",
        response_model=DocumentResponse,
    )
    def get_document(
        request: Request,
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
            request_id = getattr(request.state, "request_id", "unknown")
            logger.info(
                "Not found",
                extra={
                    "request_id": request_id,
                    "error_code": "not_found",
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "method": request.method,
                    "path": request.url.path,
                },
            )
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error_response("not_found", "Document not found"),
            )

    @app.put(
        "/documents/{doc_id}",
        response_model=DocumentResponse,
    )
    def update_document(
        request: Request,
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
                request_id = getattr(request.state, "request_id", "unknown")
                logger.info(
                    "Version conflict",
                    extra={
                        "request_id": request_id,
                        "error_code": "version_conflict",
                        "status_code": status.HTTP_409_CONFLICT,
                        "method": request.method,
                        "path": request.url.path,
                    },
                )
                return JSONResponse(
                    status_code=status.HTTP_409_CONFLICT,
                    content=error_response(
                        "version_conflict",
                        f"Expected version {if_match}, but document is at version {doc.version}",
                    ),
                )
            service.update(doc_id, payload.title, payload.content)
            doc = service.get(doc_id)
            return DocumentResponse.model_validate(doc)
        except KeyError:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.info(
                "Not found",
                extra={
                    "request_id": request_id,
                    "error_code": "not_found",
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "method": request.method,
                    "path": request.url.path,
                },
            )
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error_response("not_found", "Document not found"),
            )

    @app.post(
        "/documents/{doc_id}/submit",
        response_model=DocumentResponse,
    )
    def submit_document(
        request: Request,
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
                request_id = getattr(request.state, "request_id", "unknown")
                logger.info(
                    "Version conflict",
                    extra={
                        "request_id": request_id,
                        "error_code": "version_conflict",
                        "status_code": status.HTTP_409_CONFLICT,
                        "method": request.method,
                        "path": request.url.path,
                    },
                )
                return JSONResponse(
                    status_code=status.HTTP_409_CONFLICT,
                    content=error_response(
                        "version_conflict",
                        f"Expected version {if_match}, but document is at version {doc.version}",
                    ),
                )
            service.submit(doc_id)
            doc = service.get(doc_id)
            return DocumentResponse.model_validate(doc)
        except KeyError:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.info(
                "Not found",
                extra={
                    "request_id": request_id,
                    "error_code": "not_found",
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "method": request.method,
                    "path": request.url.path,
                },
            )
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error_response("not_found", "Document not found"),
            )

    @app.post(
        "/documents/{doc_id}/approve",
        response_model=DocumentResponse,
    )
    def approve_document(
        request: Request,
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
                request_id = getattr(request.state, "request_id", "unknown")
                logger.info(
                    "Version conflict",
                    extra={
                        "request_id": request_id,
                        "error_code": "version_conflict",
                        "status_code": status.HTTP_409_CONFLICT,
                        "method": request.method,
                        "path": request.url.path,
                    },
                )
                return JSONResponse(
                    status_code=status.HTTP_409_CONFLICT,
                    content=error_response(
                        "version_conflict",
                        f"Expected version {if_match}, but document is at version {doc.version}",
                    ),
                )
            service.approve(doc_id)
            doc = service.get(doc_id)
            return DocumentResponse.model_validate(doc)
        except KeyError:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.info(
                "Not found",
                extra={
                    "request_id": request_id,
                    "error_code": "not_found",
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "method": request.method,
                    "path": request.url.path,
                },
            )
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error_response("not_found", "Document not found"),
            )

    @app.post(
        "/documents/{doc_id}/reject",
        response_model=DocumentResponse,
    )
    def reject_document(
        request: Request,
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
                request_id = getattr(request.state, "request_id", "unknown")
                logger.info(
                    "Version conflict",
                    extra={
                        "request_id": request_id,
                        "error_code": "version_conflict",
                        "status_code": status.HTTP_409_CONFLICT,
                        "method": request.method,
                        "path": request.url.path,
                    },
                )
                return JSONResponse(
                    status_code=status.HTTP_409_CONFLICT,
                    content=error_response(
                        "version_conflict",
                        f"Expected version {if_match}, but document is at version {doc.version}",
                    ),
                )
            service.reject(doc_id)
            doc = service.get(doc_id)
            return DocumentResponse.model_validate(doc)
        except KeyError:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.info(
                "Not found",
                extra={
                    "request_id": request_id,
                    "error_code": "not_found",
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "method": request.method,
                    "path": request.url.path,
                },
            )
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error_response("not_found", "Document not found"),
            )

    @app.get("/health/live")
    def health() -> dict[str, str]:
        """Liveness check endpoint."""
        return {"status": "ok"}

    @app.get("/health/ready", response_model=None)
    def readiness(request: Request) -> dict[str, str] | JSONResponse:
        """Readiness check endpoint."""
        try:
            session_factory = get_session_factory()
            with session_factory() as session:
                session.execute(select(DocumentModel.id).limit(1))
                session.execute(select(IdempotencyKeyModel.id).limit(1))
            return {"status": "ready"}
        except Exception:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.info(
                "Database unavailable",
                extra={
                    "request_id": request_id,
                    "error_code": "db_unavailable",
                    "status_code": status.HTTP_503_SERVICE_UNAVAILABLE,
                    "method": request.method,
                    "path": request.url.path,
                },
            )
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=error_response("db_unavailable", "Database unavailable"),
            )

    return app


app = create_app()
