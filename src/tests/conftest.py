"""Pytest configuration for tests using the dedicated test database."""

from collections.abc import Generator
import os
from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import delete
from sqlalchemy.engine import make_url

from config import Settings
from infrastructure.database import get_session_factory
from infrastructure.models import DocumentModel, IdempotencyKeyModel


def _get_validated_test_database_url() -> str:
    settings = Settings()
    test_database_url = settings.test_database_url

    if test_database_url == settings.database_url:
        raise RuntimeError("TEST_DATABASE_URL must differ from DATABASE_URL")

    test_database_name = make_url(test_database_url).database or ""
    if "test" not in test_database_name:
        raise RuntimeError("TEST_DATABASE_URL must target a dedicated test database")

    return test_database_url


TEST_DATABASE_URL = _get_validated_test_database_url()

# Ensure all app imports during pytest bind to the isolated test database.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL


def _get_alembic_config(database_url: str) -> Config:
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _clear_test_data() -> None:
    session_factory = get_session_factory()
    with session_factory() as session, session.begin():
        session.execute(delete(IdempotencyKeyModel))
        session.execute(delete(DocumentModel))


@pytest.fixture(scope="session", autouse=True)
def setup_test_db() -> Generator[None, None, None]:
    """Apply migrations to the dedicated test database once per test session."""
    command.upgrade(_get_alembic_config(TEST_DATABASE_URL), "head")
    _clear_test_data()
    yield


@pytest.fixture(autouse=True)
def isolate_test_data() -> Generator[None, None, None]:
    """Clear application rows while preserving the migrated schema."""
    _clear_test_data()
    yield
    _clear_test_data()
