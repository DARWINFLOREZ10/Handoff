from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "FlowForge Platform"
    environment: str = "local"
    debug: bool = False
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://flowforge:flowforge@localhost:5432/flowforge"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret_key: str = Field(default="change-me-in-production", repr=False)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    google_client_id: str = ""
    google_client_secret: str = Field(default="", repr=False)
    google_oauth_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"

    cors_origins: str = "http://localhost:3000"
    free_plan_max_requests_per_minute: int = 60
    pro_plan_max_requests_per_minute: int = 600

    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
