"""Configuration owned by the isolated AI review deployment."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AIReviewSettings(BaseSettings):
    """Environment settings with no dependency on the core application's config."""

    model_config = SettingsConfigDict(env_prefix="AI_REVIEW_", env_file=".env", extra="ignore")

    database_path: str = "var/ai-review.sqlite3"
    provider: Literal["rule_based", "gemini", "groq"] = "groq"
    gemini_api_key: str | None = Field(default=None, repr=False)
    gemini_model: str = "gemini-2.5-flash"
    groq_api_key: str | None = Field(default=None, repr=False)
    groq_model: str = "llama-3.1-8b-instant"
    provider_timeout_seconds: float = Field(default=8.0, gt=0, le=120)
    provider_max_attempts: int = Field(default=2, ge=1, le=5)
    provider_retry_backoff_seconds: float = Field(default=0.25, ge=0, le=30)
    job_max_attempts: int = Field(default=3, ge=1, le=10)
    auto_process_jobs: bool = True
    local_worker_max_concurrency: int = Field(default=1, ge=1, le=4)
    local_worker_retry_delay_seconds: float = Field(default=0.25, ge=0, le=60)
    service_token: str | None = Field(default=None, repr=False)

    @field_validator("service_token", mode="before")
    @classmethod
    def normalise_service_token(cls, value: object) -> str | None:
        """Treat an empty environment variable as authentication disabled."""

        if value is None:
            return None
        token = str(value).strip()
        return token or None
