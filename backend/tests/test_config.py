import pytest
from app.core.config import Settings


def test_settings_required_fields():
    settings = Settings(
        _env_file=None,
        database_url="postgresql://user:pass@localhost/db",
        jwt_secret="test-secret",
        s3_bucket="test-bucket",
        deployment_environment="test",
    )
    assert settings.database_url == "postgresql://user:pass@localhost/db"
    assert settings.jwt_secret == "test-secret"
    assert settings.s3_bucket == "test-bucket"


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch):
    # Settings intentionally accept deployment environment overrides. Remove
    # host-specific AWS variables so this test exercises declared defaults.
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)
    settings = Settings(
        _env_file=None,
        database_url="postgresql://user:pass@localhost/db",
        jwt_secret="test-secret",
        s3_bucket="test-bucket",
        deployment_environment="test",
    )
    assert settings.jwt_algorithm == "HS256"
    assert settings.access_token_expire_minutes == 1440
    assert settings.smtp_host == "localhost"
    assert settings.smtp_port == 1025
    assert settings.smtp_from == "no-reply@presidio.com"
    assert settings.aws_region == "us-east-1"


def test_settings_parse_cors_origins_from_a_comma_separated_value():
    settings = Settings(
        database_url="postgresql://user:pass@localhost/db",
        jwt_secret="test-secret",
        s3_bucket="test-bucket",
        deployment_environment="test",
        cors_origins="https://app.example.com, https://preview.example.com,",
    )

    assert settings.cors_origins_list == [
        "https://app.example.com",
        "https://preview.example.com",
    ]


def test_production_rejects_wildcard_cors_and_local_storage():
    with pytest.raises(ValueError, match="CORS_ORIGINS"):
        Settings(
            _env_file=None,
            database_url="postgresql://user:pass@localhost/db",
            jwt_secret="test-secret",
            deployment_environment="production",
            cors_origins="*",
            storage_backend="azure",
            azure_storage_account_url="https://example.blob.core.windows.net",
        )


def test_production_rejects_enabled_email_delivery_without_azure_communication_settings():
    with pytest.raises(ValueError, match="AZURE_COMMUNICATION_CONNECTION_STRING"):
        Settings(
            _env_file=None,
            database_url="postgresql://user:pass@localhost/db",
            jwt_secret="test-secret",
            deployment_environment="production",
            cors_origins="https://app.example.com",
            storage_backend="azure",
            azure_storage_account_url="https://example.blob.core.windows.net",
            email_delivery_enabled=True,
            azure_communication_connection_string="",
            azure_communication_sender="",
        )
