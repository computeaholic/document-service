"""API request/response schemas."""

from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from enum import Enum


class DocumentStatus(str, Enum):
    """Document status enumeration."""

    draft = "draft"
    submitted = "submitted"
    approved = "approved"
    rejected = "rejected"


class CreateDocumentRequest(BaseModel):
    """Request schema for creating a document."""

    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)


class UpdateDocumentRequest(BaseModel):
    """Request schema for updating a document."""

    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)


class DocumentResponse(BaseModel):
    """Response schema for document data."""

    id: UUID
    title: str
    content: str
    status: DocumentStatus
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
