"""Configuration owned by the receipt-intelligence deployment."""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ReceiptIntelligenceSettings(BaseSettings):
    """Environment settings with no dependency on the core application config."""

    model_config = SettingsConfigDict(
        env_prefix="RECEIPT_INTELLIGENCE_",
        env_file=".env",
        extra="ignore",
    )

    database_path: str = "var/receipt-intelligence.sqlite3"
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
