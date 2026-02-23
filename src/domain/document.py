from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable
from uuid import UUID, uuid4

from .exceptions import IllegalTransitionError, ValidationError


class Status(str, Enum):
    draft = "draft"
    submitted = "submitted"
    approved = "approved"
    rejected = "rejected"


@dataclass
class Document:
    id: UUID = field(default_factory=uuid4)
    title: str = ""
    content: str = ""
    status: Status = Status.draft
    version: int = 0
    clock: Callable[[], datetime] = field(
        default=lambda: datetime.now(timezone.utc), repr=False, compare=False
    )
    created_at: datetime = field(init=False)
    updated_at: datetime = field(init=False)

    def __post_init__(self) -> None:
        if self.version < 0:
            raise ValidationError("version must be non-negative")

        now = self.clock()
        self.created_at = now
        self.updated_at = now

        self.title = self.title.strip()
        if not self.title:
            raise ValidationError("title must be non-empty")
        if len(self.title) > 200:
            raise ValidationError("title exceeds max length 200")

    def _bump(self) -> None:
        # Increment version and update timestamp for every successful mutation
        self.version += 1
        self.updated_at = self.clock()

    def update(self, title: str, content: str) -> None:
        if self.status != Status.draft:
            raise IllegalTransitionError("update allowed only in draft state")

        stripped_title = title.strip()
        if not stripped_title:
            raise ValidationError("title must be non-empty")
        if len(stripped_title) > 200:
            raise ValidationError("title exceeds max length 200")

        self.title = stripped_title
        self.content = content
        self._bump()

    def submit(self) -> None:
        if self.status != Status.draft:
            raise IllegalTransitionError("submit allowed only in draft state")
        if not self.content.strip():
            raise ValidationError("content must be non-empty when submitting")
        self.status = Status.submitted
        self._bump()

    def approve(self) -> None:
        if self.status != Status.submitted:
            raise IllegalTransitionError("approve allowed only in submitted state")
        self.status = Status.approved
        self._bump()

    def reject(self) -> None:
        if self.status != Status.submitted:
            raise IllegalTransitionError("reject allowed only in submitted state")
        self.status = Status.rejected
        self._bump()
