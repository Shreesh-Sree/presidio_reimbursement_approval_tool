import functools
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    jwt_secret: str
    # Browser users authenticate through Clerk in normal deployments.  ``local``
    # remains an explicit migration/test-only mode so existing password hashes
    # can be retired without opening a second browser sign-in path.
    auth_provider: Literal["clerk", "local"] = "clerk"
    clerk_jwks_url: str = ""
    clerk_issuer: str = ""
    clerk_audience: str = ""
    clerk_authorized_parties: str = ""
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
    # Approval tasks are human work, so the default is deliberately measured
    # in days. A deployment can shorten this with APPROVAL_SLA_HOURS.
    approval_sla_hours: int = Field(default=72, ge=1, le=24 * 30)
    aws_region: str = "us-east-1"
    # S3 is required only when STORAGE_BACKEND=s3; local storage is the safe
    # development default and should not require placeholder cloud credentials.
    s3_bucket: str = ""
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        """Return a whitespace-safe list suitable for FastAPI CORS middleware."""

        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def clerk_authorized_parties_list(self) -> list[str]:
        """Return configured first-party origins for Clerk's ``azp`` claim."""

        return [party.strip().rstrip("/") for party in self.clerk_authorized_parties.split(",") if party.strip()]


@functools.lru_cache
def get_settings() -> Settings:
    return Settings()
