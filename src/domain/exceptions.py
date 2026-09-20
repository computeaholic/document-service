"""Domain exceptions for document-service."""


class IllegalTransitionError(Exception):
    """Raised when an invalid state transition is attempted on a Document."""


class ValidationError(Exception):
    """Raised when domain validation fails (e.g. empty content on submit)."""


class VersionConflictError(Exception):
    """Raised when a concurrent write wins between read and persisted update."""
