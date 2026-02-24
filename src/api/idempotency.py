"""Idempotency middleware for POST /documents endpoint."""

import hashlib
import json
from typing import Any
from uuid import uuid4

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import IntegrityError

from infrastructure.models import IdempotencyKeyModel


def get_request_hash(request_body: dict[str, Any]) -> str:
    """Generate SHA-256 hash of request body.

    Args:
        request_body: Request body dictionary

    Returns:
        SHA-256 hash hex string
    """
    body_json = json.dumps(request_body, sort_keys=True)
    return hashlib.sha256(body_json.encode()).hexdigest()


def check_idempotency(
    idempotency_key: str,
    request_body: dict[str, Any],
    session_factory: sessionmaker[Session],
) -> tuple[bool, str | None]:
    """Check if request is duplicate based on idempotency key.

    Args:
        idempotency_key: Idempotency-Key header value
        request_body: Parsed request body
        session_factory: SQLAlchemy session factory

    Returns:
        Tuple of (is_duplicate, stored_response_body)
        - If is_duplicate=True and response_body is not None, return stored response
        - If is_duplicate=True and response_body is None, means same key but different hash (return 400)
        - If is_duplicate=False, proceed with request
    """
    request_hash = get_request_hash(request_body)

    with session_factory() as session:
        existing = (
            session.query(IdempotencyKeyModel)
            .filter(IdempotencyKeyModel.key == idempotency_key)
            .first()
        )

        if existing is None:
            # New idempotency key, proceed
            return (False, None)

        if existing.request_hash == request_hash:
            # Same key, same hash → return stored response
            return (True, existing.response_body)
        else:
            # Same key, different hash → conflict
            return (True, None)


def store_idempotency(
    idempotency_key: str,
    request_body: dict[str, Any],
    response_body: dict[str, Any],
    session_factory: sessionmaker[Session],
) -> None:
    """Store idempotency record after successful request.

    Args:
        idempotency_key: Idempotency-Key header value
        request_body: Parsed request body
        response_body: Response body dictionary
        session_factory: SQLAlchemy session factory
    """
    request_hash = get_request_hash(request_body)
    response_json = json.dumps(response_body)

    with session_factory() as session:
        with session.begin():
            record = IdempotencyKeyModel(
                id=uuid4(),
                key=idempotency_key,
                request_hash=request_hash,
                response_body=response_json,
            )
            session.add(record)
