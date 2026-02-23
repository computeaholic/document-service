"""Application configuration."""

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    model_config = ConfigDict(env_file=".env")

    app_name: str = "Document Service"
    app_version: str = "0.1.0"
    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/documents"
    )
