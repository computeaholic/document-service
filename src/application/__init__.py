"""Application service layer for document-service.

Orchestrates domain operations without introducing persistence or framework dependencies.
Pure orchestration layer for use cases.
"""

from .services import DocumentService

__all__ = ["DocumentService"]
