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

    # Rate Limiting & Usage Quotas (Phase 3)
    rate_limit_dev_rpm: int = 10
    rate_limit_dev_monthly: int = 1000

    rate_limit_standard_rpm: int = 60
    rate_limit_standard_monthly: int = 25000

    rate_limit_higher_rpm: int = 120
    rate_limit_higher_monthly: int = 100000

    rate_limit_burst_multiplier: float = 1.0
    usage_event_retention_days: int = 90

    def get_tier_limits(self, tier: str) -> dict:
        """Return rate limit (rpm) and monthly request quota for a given tier."""
        normalized = (tier or "development").strip().lower()
        if normalized in ("standard",):
            return {
                "tier": "standard",
                "rpm": self.rate_limit_standard_rpm,
                "monthly": self.rate_limit_standard_monthly,
            }
        elif normalized in ("higher-volume", "higher_volume", "higher"):
            return {
                "tier": "higher-volume",
                "rpm": self.rate_limit_higher_rpm,
                "monthly": self.rate_limit_higher_monthly,
            }
        return {
            "tier": "development",
            "rpm": self.rate_limit_dev_rpm,
            "monthly": self.rate_limit_dev_monthly,
        }

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
