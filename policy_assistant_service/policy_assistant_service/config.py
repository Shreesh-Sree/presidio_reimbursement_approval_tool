"""Configuration owned solely by the policy assistant deployment."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class PolicyAssistantSettings(BaseSettings):
    """Safe defaults for a local, independently persisted RAG service."""

    model_config = SettingsConfigDict(
        env_prefix="POLICY_ASSISTANT_", env_file=".env", extra="ignore"
    )

    database_path: str = "var/policy-assistant.sqlite3"
    service_token: SecretStr = Field(..., min_length=16, repr=False)
    max_document_chars: int = Field(default=50_000, ge=500, le=250_000)
    max_question_chars: int = Field(default=1_200, ge=50, le=10_000)
    chunk_size_chars: int = Field(default=900, ge=300, le=3_000)
    chunk_overlap_chars: int = Field(default=120, ge=0, le=500)
    default_top_k: int = Field(default=3, ge=1, le=8)
    minimum_similarity: float = Field(default=0.08, ge=0, le=1)
    embedding_dimensions: int = Field(default=192, ge=64, le=1_024)

    # External LLM providers are deliberately opt-in and are never contacted by
    # this initial local implementation. Keeping the switch explicit prevents a
    # future configuration change from silently exporting policy documents.
    provider_mode: Literal["deterministic", "openrouter", "huggingface"] = "deterministic"
    enable_external_provider: bool = False
    openrouter_api_key: SecretStr | None = Field(default=None, repr=False)
    huggingface_api_key: SecretStr | None = Field(default=None, repr=False)

    @field_validator("database_path", mode="before")
    @classmethod
    def require_local_sqlite(cls, value: object) -> str:
        """Reject any network/core database URL before a connection is attempted."""

        raw = str(value).strip()
        lowered = raw.lower()
        forbidden_schemes = (
            "postgres:",
            "postgresql:",
            "postgresql+",
            "mysql:",
            "mariadb:",
            "mssql:",
            "oracle:",
        )
        if not raw or lowered.startswith(forbidden_schemes):
            raise ValueError("POLICY_ASSISTANT_DATABASE_PATH must be a local SQLite path")

        if lowered.startswith("sqlite:///"):
            raw = raw[len("sqlite:///") :]
        elif "://" in raw:
            raise ValueError("only local SQLite paths are supported by the policy assistant")

        if not raw or raw.startswith("//"):
            raise ValueError("POLICY_ASSISTANT_DATABASE_PATH must be a local SQLite path")
        return raw

    @field_validator("service_token", mode="before")
    @classmethod
    def trim_service_token(cls, value: object) -> str:
        token = str(value or "").strip()
        if not token:
            raise ValueError("POLICY_ASSISTANT_SERVICE_TOKEN is required")
        return token

    @model_validator(mode="after")
    def validate_chunk_settings(self) -> "PolicyAssistantSettings":
        if self.chunk_overlap_chars >= self.chunk_size_chars:
            raise ValueError("chunk_overlap_chars must be smaller than chunk_size_chars")
        return self
