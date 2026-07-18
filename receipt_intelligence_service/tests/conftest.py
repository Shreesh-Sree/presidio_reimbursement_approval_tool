from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from receipt_intelligence_service.api import create_app
from receipt_intelligence_service.config import ReceiptIntelligenceSettings
from receipt_intelligence_service.persistence import InMemoryDigestRepository
from receipt_intelligence_service.service import ReceiptIntelligenceService
from receipt_intelligence_service.providers import ResilientReceiptProvider


@pytest.fixture
def service_token() -> str:
    return "receipt-intelligence-test-token"


@pytest.fixture
def client(service_token: str):
    settings = ReceiptIntelligenceSettings(
        service_token=service_token,
        max_file_bytes=1_024,
        max_text_chars=2_000,
    )
    provider = ResilientReceiptProvider(None)
    service = ReceiptIntelligenceService(InMemoryDigestRepository(), settings, provider)
    with TestClient(create_app(service, settings=settings)) as test_client:
        yield test_client


@pytest.fixture
def valid_payload() -> dict[str, object]:
    return {
        "organization_scope": "org:opaque-123",
        "receipt": {
            "sha256_digest": "a" * 64,
            "media_type": "application/pdf",
            "size_bytes": 512,
            "text_source": "not_provided",
        },
        "policy": {
            "expense_amount": "42.50",
            "currency": "USD",
            "receipt_required_at_or_above": "25.00",
        },
    }


def authorization_headers(service_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {service_token}"}
