"""Pytest configuration for integration tests."""

import pytest

from infrastructure.database import Base, get_engine


@pytest.fixture(scope="session", autouse=True)
def setup_test_db() -> None:
    """Create a clean schema for integration tests."""
    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
