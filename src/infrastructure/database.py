"""Database configuration and session factory."""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import Settings


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


def get_engine() -> Engine:
    """Create a database engine from settings."""
    settings = Settings()
    return create_engine(settings.database_url, echo=False)


def get_session_factory() -> sessionmaker[Session]:
    """Create a session factory for database access."""
    engine = get_engine()
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)
