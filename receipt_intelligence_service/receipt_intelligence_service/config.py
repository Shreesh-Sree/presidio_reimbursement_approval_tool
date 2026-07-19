"""Configuration owned by the receipt-intelligence deployment."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ReceiptIntelligenceSettings(BaseSettings):
    """Environment settings with no dependency on the core application config."""

    model_config = SettingsConfigDict(
        env_prefix="RECEIPT_INTELLIGENCE_",
        env_file=".env",
        extra="ignore",
    )

    environment: Literal["local", "test", "staging", "production"] = "production"
    persistence_backend: Literal["sqlite", "postgresql"] = "sqlite"
    database_path: str = "var/receipt-intelligence.sqlite3"
    database_url: str | None = Field(default=None, repr=False)
    service_token: str | None = Field(default=None, repr=False)
    max_file_bytes: int = Field(default=10 * 1024 * 1024, ge=1, le=100 * 1024 * 1024)
    max_text_chars: int = Field(default=24_000, ge=256, le=100_000)
    allowed_media_types: tuple[str, ...] = (
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/webp",
    )
    log_level: str = "INFO"
    ocr_enabled: bool = True
    ocr_languages: str = "eng"
    max_ocr_bytes: int = Field(default=10 * 1024 * 1024, ge=1, le=100 * 1024 * 1024)

    # Groq LLM — primary receipt extraction when configured; rule-based is fallback.
    groq_api_key: str | None = Field(default=None, repr=False)
    groq_model: str = "llama-3.1-8b-instant"
    groq_timeout_seconds: float = Field(default=8.0, ge=1.0, le=30.0)
    groq_max_attempts: int = Field(default=2, ge=1, le=5)
    # External LLM use is fail-closed. A caller must separately attest that
    # the organization has opted in for this event.
    groq_external_egress_enabled: bool = False
    groq_max_text_chars: int = Field(default=2_000, ge=256, le=12_000)
    max_ocr_pixels: int = Field(default=20_000_000, ge=1_000_000, le=100_000_000)

    @field_validator("service_token", mode="before")
    @classmethod
    def normalise_service_token(cls, value: object) -> str | None:
        if value is None:
            return None
        token = str(value).strip()
        return token or None

    @field_validator("allowed_media_types")
    @classmethod
    def normalise_media_types(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        cleaned = tuple(sorted({value.strip().lower() for value in values if value.strip()}))
        if not cleaned:
            raise ValueError("at least one allowed media type is required")
        return cleaned

    @model_validator(mode="after")
    def require_durable_authenticated_runtime(self) -> "ReceiptIntelligenceSettings":
        if self.environment in {"local", "test"}:
            return self
        missing: list[str] = []
        if not self.service_token:
            missing.append("RECEIPT_INTELLIGENCE_SERVICE_TOKEN")
        if self.persistence_backend != "postgresql":
            missing.append("RECEIPT_INTELLIGENCE_PERSISTENCE_BACKEND=postgresql")
        if not self.database_url:
            missing.append("RECEIPT_INTELLIGENCE_DATABASE_URL")
        if missing:
            raise ValueError(
                "staging and production receipt intelligence deployments require durable "
                f"authenticated configuration: {', '.join(missing)}"
            )
        return self
