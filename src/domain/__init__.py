"""Domain package for document-service.

Exports domain types for easy imports in tests and other modules.
"""

from .document import Document, Status
from .exceptions import IllegalTransitionError, ValidationError

__all__ = [
    "Document",
    "Status",
    "IllegalTransitionError",
    "ValidationError",
]
