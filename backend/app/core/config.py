import functools

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    jwt_secret: str
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
    aws_region: str = "us-east-1"
    # S3 is required only when STORAGE_BACKEND=s3; local storage is the safe
    # development default and should not require placeholder cloud credentials.
    s3_bucket: str = ""
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        """Return a whitespace-safe list suitable for FastAPI CORS middleware."""

        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@functools.lru_cache
def get_settings() -> Settings:
    return Settings()
