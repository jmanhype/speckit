"""Application configuration management."""
from typing import List
from pydantic import Field, PostgresDsn, RedisDsn, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "MarketPrep API"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = Field(default="development", pattern="^(development|staging|production)$")

    # API
    api_v1_prefix: str = "/api/v1"
    allowed_hosts: List[str] = Field(default_factory=lambda: ["*"])
    cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # Database
    database_url: PostgresDsn = Field(
        default="postgresql://marketprep:devpassword@localhost:5432/marketprep_dev"
    )
    db_echo: bool = False
    db_pool_size: int = 10
    db_max_overflow: int = 100

    # Redis
    redis_url: RedisDsn = Field(default="redis://localhost:6379/0")
    redis_cache_ttl: int = 3600  # 1 hour default

    # Security
    secret_key: str = Field(default="dev-secret-key-change-in-production-min32chars")
    encryption_key: str = Field(default="dev-encryption-key-32-bytes-minimum-length")
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"

    # Square API
    square_application_id: str = ""
    square_application_secret: str = ""
    square_environment: str = Field(default="sandbox", pattern="^(sandbox|production)$")
    square_oauth_redirect_uri: str = "http://localhost:3000/auth/square/callback"

    # Weather API
    openweather_api_key: str = ""

    # Events API
    eventbrite_api_key: str = ""

    # Stripe
    stripe_api_key: str = ""
    stripe_webhook_secret: str = ""

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/1"

    # Observability
    sentry_dsn: str = ""
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    log_file: str = ""  # Optional file path for error logs

    @validator("encryption_key")
    def validate_encryption_key_length(cls, v: str) -> str:
        """Ensure encryption key is at least 32 bytes."""
        if len(v.encode()) < 32:
            raise ValueError("Encryption key must be at least 32 bytes")
        return v


# Global settings instance
settings = Settings()
