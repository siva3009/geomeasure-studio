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
    allowed_origins: str = "http://localhost:5173,https://geomeasure-studio.vercel.app"

    # Supabase Auth
    supabase_jwt_secret: str = ""
    supabase_url: str = "https://egvoacfdtynoafsqlmol.supabase.co"

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

    # Phase 4: AI Copilot with Low-Latency Hybrid Inference
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3.5:2b"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    ai_fallback_api_key: str = ""
    ai_fallback_base_url: str = ""
    ai_fallback_model: str = ""
    ai_provider_mode: str = "local_first"  # local_first, hosted_first, local_only, hosted_only
    ai_privacy_mode: str = "standard"  # standard, local_only
    ai_request_timeout_seconds: float = 12.0
    ai_max_output_tokens: int = 1024
    ai_rate_limit_rpm: int = 15
    ai_monthly_quota: int = 500

    @property
    def effective_ai_provider_mode(self) -> str:
        """Enforces safe routing: prevents cloud backends from querying localhost Ollama."""
        if self.ai_privacy_mode == "local_only":
            return "local_only"
        if self.environment == "production":
            is_local = any(h in self.ollama_base_url.lower() for h in ("localhost", "127.0.0.1", "0.0.0.0", "::1"))
            if is_local:
                return "hosted_only" if self.ai_provider_mode == "hosted_only" else "hosted_first"
        return self.ai_provider_mode

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
