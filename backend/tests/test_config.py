import pytest
from app.core.config import Settings


def test_settings_required_fields():
    settings = Settings(
        database_url="postgresql://user:pass@localhost/db",
        jwt_secret="test-secret",
        s3_bucket="test-bucket",
    )
    assert settings.database_url == "postgresql://user:pass@localhost/db"
    assert settings.jwt_secret == "test-secret"
    assert settings.s3_bucket == "test-bucket"


def test_settings_defaults():
    settings = Settings(
        database_url="postgresql://user:pass@localhost/db",
        jwt_secret="test-secret",
        s3_bucket="test-bucket",
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
        cors_origins="https://app.example.com, https://preview.example.com,",
    )

    assert settings.cors_origins_list == [
        "https://app.example.com",
        "https://preview.example.com",
    ]
