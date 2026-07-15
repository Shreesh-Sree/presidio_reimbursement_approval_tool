"""Configuration owned by the isolated AI review deployment."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AIReviewSettings(BaseSettings):
    """Environment settings with no dependency on the core application's config."""

    model_config = SettingsConfigDict(env_prefix="AI_REVIEW_", env_file=".env", extra="ignore")

    database_path: str = "var/ai-review.sqlite3"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    provider_timeout_seconds: float = Field(default=8.0, gt=0, le=120)
    provider_max_attempts: int = Field(default=2, ge=1, le=5)
    provider_retry_backoff_seconds: float = Field(default=0.25, ge=0, le=30)
    job_max_attempts: int = Field(default=3, ge=1, le=10)
