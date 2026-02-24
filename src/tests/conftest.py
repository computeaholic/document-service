"""Pytest configuration for integration tests."""

from collections.abc import Generator

import pytest

from infrastructure.database import Base, get_engine


@pytest.fixture(scope="session", autouse=True)
def setup_test_db() -> Generator[None, None, None]:
    """Create a clean schema for integration tests."""
    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
