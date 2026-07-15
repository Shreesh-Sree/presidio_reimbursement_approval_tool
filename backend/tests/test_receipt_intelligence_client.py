"""Transport-level privacy and authentication coverage for receipt intelligence."""

from __future__ import annotations

from decimal import Decimal
import json
from uuid import UUID

from app.services import receipt_intelligence_client


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return json.dumps({"findings": [], "ocr": {"performed": False}}).encode("utf-8")


def test_client_uses_bearer_auth_and_sends_only_metadata_with_opaque_references(monkeypatch):
    organization_id = UUID("11111111-1111-1111-1111-111111111111")
    report_id = UUID("22222222-2222-2222-2222-222222222222")
    item_id = UUID("33333333-3333-3333-3333-333333333333")
    attachment_id = UUID("44444444-4444-4444-4444-444444444444")
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return _Response()

    monkeypatch.setenv("RECEIPT_INTELLIGENCE_SERVICE_URL", "http://receipt-intelligence.internal")
    monkeypatch.setenv("RECEIPT_INTELLIGENCE_SERVICE_TOKEN", "receipt-service-token")
    monkeypatch.setattr(receipt_intelligence_client, "urlopen", fake_urlopen)

    result = receipt_intelligence_client.analyze_receipt(
        organization_id=organization_id,
        report_id=report_id,
        item_id=item_id,
        attachment_id=attachment_id,
        receipt_checksum="a" * 64,
        receipt_mime_type="application/pdf",
        receipt_size_bytes=123,
        expense_amount=Decimal("75.50"),
        currency="usd",
        receipt_required_at_or_above=Decimal("25.00"),
    )

    assert captured["url"] == "http://receipt-intelligence.internal/v1/analyze"
    headers = {str(key).lower(): value for key, value in dict(captured["headers"]).items()}
    assert headers["authorization"] == "Bearer receipt-service-token"
    assert headers["content-type"] == "application/json"
    assert headers["x-request-id"].startswith("receipt-")

    body = captured["body"]
    assert body == {
        "event_id": result.context.event_id,
        "event_type": "receipt.analysis.requested",
        "event_version": "1.0",
        "organization_scope": result.context.organization_ref,
        "receipt": {
            "sha256_digest": "a" * 64,
            "media_type": "application/pdf",
            "size_bytes": 123,
        },
        "policy": {
            "expense_amount": "75.50",
            "currency": "USD",
            "receipt_required_at_or_above": "25.00",
        },
    }
    assert result.context.organization_ref.startswith("tenant-")
    assert result.context.report_ref.startswith("report-")
    assert result.context.item_ref.startswith("item-")
    assert result.context.attachment_ref and result.context.attachment_ref.startswith("attachment-")
    serialized = json.dumps(body)
    for identifier in (organization_id, report_id, item_id, attachment_id):
        assert str(identifier) not in serialized
        assert identifier.hex not in serialized
