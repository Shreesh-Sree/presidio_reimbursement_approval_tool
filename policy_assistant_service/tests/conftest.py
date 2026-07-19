from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from policy_assistant_service.api import create_app
from policy_assistant_service.config import PolicyAssistantSettings


@pytest.fixture
def service_token() -> str:
    return "test-policy-assistant-token-12345"


@pytest.fixture
def auth_headers(service_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {service_token}"}


@pytest.fixture
def client(tmp_path, service_token: str):
    settings = PolicyAssistantSettings(
        environment="test",
        database_path=str(tmp_path / "policy-assistant.sqlite3"),
        service_token=service_token,
        chunk_size_chars=350,
        chunk_overlap_chars=50,
    )
    with TestClient(create_app(settings=settings)) as test_client:
        yield test_client


def index_payload(
    *,
    tenant_ref: str = "tenant-demo",
    policy_version_ref: str = "policy-travel-v2",
    document_ref: str = "doc-travel-rules",
    content: str,
) -> dict[str, str]:
    return {
        "tenant_ref": tenant_ref,
        "policy_version_ref": policy_version_ref,
        "document_ref": document_ref,
        "content": content,
    }
