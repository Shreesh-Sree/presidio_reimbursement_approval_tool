import pytest

from ai_review_service.config import AIReviewSettings


def test_production_requires_token_and_postgres_configuration():
    with pytest.raises(ValueError, match="AI_REVIEW_SERVICE_TOKEN"):
        # Explicitly override any developer .env token so this remains
        # deterministic on a configured workstation.
        AIReviewSettings(environment="production", service_token="")


def test_staging_accepts_explicit_durable_authenticated_configuration():
    settings = AIReviewSettings(
        environment="staging",
        persistence_backend="postgresql",
        database_url="postgresql://review:password@db.example/reviews",
        service_token="test-service-token",
    )

    assert settings.persistence_backend == "postgresql"
