"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env")

    app_name: str = "Document Service"
    app_version: str = "1.0.2"
    database_url: str = "postgresql+psycopg://test:test@localhost:5433/document_service"
    test_database_url: str = (
        "postgresql+psycopg://test:test@localhost:5434/document_service_test"
    )
