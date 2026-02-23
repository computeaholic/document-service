"""SQLAlchemy models for persistence."""

from uuid import UUID as PyUUID

from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database import Base


class DocumentModel(Base):
    """Document persistence model."""

    __tablename__ = "documents"

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
