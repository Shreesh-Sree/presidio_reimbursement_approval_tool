import pytest

from policy_assistant_service.config import PolicyAssistantSettings


def test_production_requires_postgres_configuration(service_token):
    with pytest.raises(ValueError, match="POLICY_ASSISTANT_PERSISTENCE_BACKEND=postgresql"):
        PolicyAssistantSettings(environment="production", service_token=service_token)


def test_staging_accepts_explicit_postgres_configuration(service_token):
    settings = PolicyAssistantSettings(
        environment="staging",
        persistence_backend="postgresql",
        database_url="postgresql://policy:password@db.example/policies",
        service_token=service_token,
    )

    assert settings.persistence_backend == "postgresql"
