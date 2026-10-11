"""
Application configuration loaded from environment variables.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Environment: development, test, production
    environment: str = "development"

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/geomeasure"
    db_connect_timeout: int = 10

    # Explicit flag to permit in-memory fallback in development
    allow_in_memory_db: bool = False

    # CORS
    allowed_origins: str = "http://localhost:5173"

    # Supabase Auth
    supabase_jwt_secret: str = ""
    supabase_url: str = ""

    # Upload limits
    max_upload_size_mb: int = 50
    max_decompressed_size_mb: int = 200

    @property
    def is_in_memory_allowed(self) -> bool:
        """Allow in-memory storage only in non-production environments when permitted or testing."""
        if self.environment == "production":
            return False
        return self.allow_in_memory_db or self.environment == "test"

    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse comma-separated origins into a list."""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def max_decompressed_size_bytes(self) -> int:
        return self.max_decompressed_size_mb * 1024 * 1024

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
