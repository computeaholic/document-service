"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env")

    app_name: str = "Document Service"
    app_version: str = "0.1.0"
    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/documents"
    )
