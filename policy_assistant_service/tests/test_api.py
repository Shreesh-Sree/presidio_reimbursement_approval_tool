from __future__ import annotations

import pytest

from .conftest import index_payload
from policy_assistant_service.config import PolicyAssistantSettings


def test_token_auth_protects_policy_endpoints(client, auth_headers):
    payload = index_payload(content="Airfare is reimbursable up to USD 500 per trip.")

    missing = client.post("/v1/policy-documents", json=payload)
    wrong = client.post(
        "/v1/policy-documents",
        json=payload,
        headers={"Authorization": "Bearer incorrect-token"},
    )
    valid = client.post("/v1/policy-documents", json=payload, headers=auth_headers)

    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert valid.status_code == 201
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/ready").json()["persistence"] == "sqlite"


def test_contracts_reject_pii_and_non_opaque_scope_references(client, auth_headers):
    response = client.post(
        "/v1/policy-documents",
        headers=auth_headers,
        json=index_payload(tenant_ref="alice@example.com", content="Meals cap is USD 75."),
    )

    assert response.status_code == 422


def test_configuration_rejects_postgresql_and_requires_a_separate_sqlite_store(service_token):
    with pytest.raises(ValueError, match="SQLite"):
        PolicyAssistantSettings(
            environment="test",
            database_path="postgresql+psycopg://core-user:secret@db.example/core",
            service_token=service_token,
        )
