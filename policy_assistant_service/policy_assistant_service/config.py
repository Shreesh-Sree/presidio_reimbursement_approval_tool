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

    persistence_backend: Literal["sqlite", "appwrite"] = "sqlite"
    database_path: str = "var/policy-assistant.sqlite3"
    appwrite_endpoint: str | None = None
    appwrite_project_id: str | None = None
    appwrite_api_key: SecretStr | None = Field(default=None, repr=False)
    appwrite_database_id: str = "presidio-policy-rag"
    appwrite_documents_table_id: str = "policy-documents"
    appwrite_chunks_table_id: str = "policy-chunks"
    service_token: SecretStr = Field(..., min_length=16, repr=False)
    max_document_chars: int = Field(default=50_000, ge=500, le=250_000)
    max_question_chars: int = Field(default=1_200, ge=50, le=10_000)
    chunk_size_chars: int = Field(default=900, ge=300, le=3_000)
    chunk_overlap_chars: int = Field(default=120, ge=0, le=500)
    default_top_k: int = Field(default=3, ge=1, le=8)
    minimum_similarity: float = Field(default=0.08, ge=0, le=1)
    embedding_dimensions: int = Field(default=192, ge=64, le=1_024)

    # Groq LLM for intelligent grounded answers (primary). Falls back to raw
    # citation display when key is absent or calls fail.
    groq_api_key: str | None = Field(default=None, repr=False)
    groq_model: str = "llama-3.1-8b-instant"
    groq_timeout_seconds: float = Field(default=8.0, ge=1.0, le=30.0)
    groq_max_attempts: int = Field(default=2, ge=1, le=5)

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
        if self.persistence_backend == "sqlite":
            raw = self.database_path.strip()
            lowered = raw.lower()
            forbidden_schemes = (
                "postgres:", "postgresql:", "postgresql+", "mysql:",
                "mariadb:", "mssql:", "oracle:",
            )
            if not raw or lowered.startswith(forbidden_schemes) or ("://" in raw and not lowered.startswith("sqlite:///")):
                raise ValueError("POLICY_ASSISTANT_DATABASE_PATH must be a local SQLite path")
        else:
            missing = [
                name for name, value in {
                    "POLICY_ASSISTANT_APPWRITE_ENDPOINT": self.appwrite_endpoint,
                    "POLICY_ASSISTANT_APPWRITE_PROJECT_ID": self.appwrite_project_id,
                    "POLICY_ASSISTANT_APPWRITE_API_KEY": self.appwrite_api_key,
                }.items() if not value
            ]
            if missing:
                raise ValueError(f"Appwrite RAG persistence is not configured: {', '.join(missing)}")
        return self
