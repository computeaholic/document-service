"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env")

    app_name: str = "Document Service"
    app_version: str = "0.1.0"
    database_url: str = (
        "postgresql+psycopg://test:test@localhost:5433/document_service_test"
    )
    test_database_url: str | None = None

    def model_post_init(self, __context: object) -> None:
        """Override database_url when TEST_DATABASE_URL is provided."""
        if self.test_database_url:
            self.database_url = self.test_database_url
