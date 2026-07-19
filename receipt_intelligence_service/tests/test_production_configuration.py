import pytest

from receipt_intelligence_service.config import ReceiptIntelligenceSettings


def test_production_requires_token_and_postgres_configuration():
    with pytest.raises(ValueError, match="RECEIPT_INTELLIGENCE_SERVICE_TOKEN"):
        # Explicitly override any developer .env token so this remains
        # deterministic on a configured workstation.
        ReceiptIntelligenceSettings(environment="production", service_token="")


def test_staging_accepts_explicit_durable_authenticated_configuration():
    settings = ReceiptIntelligenceSettings(
        environment="staging",
        persistence_backend="postgresql",
        database_url="postgresql://receipt:password@db.example/receipts",
        service_token="test-service-token",
    )

    assert settings.persistence_backend == "postgresql"
