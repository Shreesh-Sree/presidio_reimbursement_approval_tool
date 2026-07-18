import functools
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", ".env.local"), extra="ignore")

    database_url: str
    jwt_secret: str
    # Browser users authenticate through Supabase in normal deployments.
    # ``local`` remains an explicit migration/test-only mode so existing
    # password hashes can be retired without opening a second browser sign-in path.
    auth_provider: Literal["supabase", "local"] = "supabase"
    supabase_url: str = ""
    supabase_jwt_secret: str = ""
    supabase_service_role_key: str = ""
    supabase_jwks: str = ""
    # This is intentionally configuration, not source code: it is the one
    # verified OAuth email allowed to create the first application admin.
    super_admin_email: str = ""
    default_organization_name: str = "Presidio"
    default_organization_code: str = "PRESIDIO"
    default_department_name: str = "General"
    default_department_code: str = "GENERAL"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "no-reply@presidio.com"
    email_delivery_enabled: bool = False
    smtp_use_tls: bool = False
    smtp_timeout_seconds: float = 10.0
    azure_communication_connection_string: str = ""
    azure_communication_sender: str = ""
    # Approval tasks are human work, so the default is deliberately measured
    # in days. A deployment can shorten this with APPROVAL_SLA_HOURS.
    approval_sla_hours: int = Field(default=72, ge=1, le=24 * 30)
    aws_region: str = "us-east-1"
    # Object storage remains optional in development. Production uses Appwrite
    # through a server-only API key; S3 is retained as a migration target.
    s3_bucket: str = ""
    appwrite_endpoint: str = ""
    appwrite_project_id: str = ""
    appwrite_api_key: str = ""
    appwrite_bucket_id: str = "presidio-private-files"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    azure_storage_connection_string: str = ""
    azure_storage_container: str = "uploads"
    # Each advisory service is independently deployed and persisted. The core
    # application only owns these narrow HTTP-boundary settings.
    ai_review_service_url: str = ""
    ai_review_service_token: str = ""
    ai_review_reference_hmac_key: str = ""
    ai_review_timeout_seconds: float = Field(default=2.0, ge=0.1, le=30.0)
    receipt_intelligence_service_url: str = ""
    receipt_intelligence_service_token: str = ""
    receipt_intelligence_timeout_seconds: float = Field(default=4.0, ge=0.1, le=30.0)
    policy_assistant_service_url: str = ""
    policy_assistant_service_token: str = ""
    policy_assistant_reference_hmac_key: str = ""
    policy_assistant_timeout_seconds: float = Field(default=4.0, ge=0.1, le=30.0)
    rate_limit_enabled: bool = True

    @property
    def cors_origins_list(self) -> list[str]:
        """Return a whitespace-safe list suitable for FastAPI CORS middleware."""

        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]




@functools.lru_cache
def get_settings() -> Settings:
    return Settings()
