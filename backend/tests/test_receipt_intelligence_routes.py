"""Manual, metadata-only receipt intelligence boundary coverage."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.routes import receipt_intelligence
from app.core.database import get_db
from app.models.attachment import Attachment
from app.models.expense_item import ExpenseItem
from app.models.policy import PolicyRule
from app.services import receipt_intelligence_client
from app.services.report_service import create_draft


def _client_for_receipt_intelligence(engine, seeded_user):
    app = FastAPI()
    app.include_router(receipt_intelligence.router)

    def override_db():
        session = Session(engine)
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    for route in receipt_intelligence.router.routes:
        for dependency in route.dependant.dependencies:
            if dependency.call is not get_db:
                app.dependency_overrides[dependency.call] = lambda: {
                    "user_id": str(seeded_user.id),
                    "organization_id": str(seeded_user.organization_id),
                    "email": seeded_user.email,
                    "roles": ["employee"],
                    "permissions": ["report:read"],
                }
    return TestClient(app)


def _report_item_and_receipt(db, seeded_user, seeded_policy, seeded_category):
    db.add(
        PolicyRule(
            policy_id=seeded_policy.id,
            category_id=seeded_category.id,
            receipt_required_above=Decimal("25.00"),
        )
    )
    report = create_draft(db, seeded_user.id, seeded_user.department_id, "Confidential client travel")
    report.applied_policy_id = seeded_policy.id
    item = ExpenseItem(
        expense_report_id=report.id,
        line_number=1,
        category_id=seeded_category.id,
        merchant_name="Private Merchant",
        amount=Decimal("75.50"),
        original_amount=Decimal("75.50"),
        currency_code="USD",
        expense_date=date.today(),
        description="Do not disclose employee@example.com or this description",
    )
    db.add(item)
    db.flush()
    receipt = Attachment(
        entity_type="expense_item_receipt",
        entity_id=item.id,
        file_name="confidential-receipt.pdf",
        original_file_name="confidential-receipt.pdf",
        storage_path="local://test/confidential-receipt.pdf",
        mime_type="application/pdf",
        file_size_bytes=321,
        checksum="a" * 64,
        uploaded_by=seeded_user.id,
    )
    db.add(receipt)
    db.commit()
    return report, item, receipt


def test_receipt_analysis_sends_only_authorized_metadata_and_returns_advice(
    engine,
    db,
    seeded_user,
    seeded_policy,
    seeded_category,
    monkeypatch,
):
    report, item, receipt = _report_item_and_receipt(db, seeded_user, seeded_policy, seeded_category)
    captured: dict[str, object] = {}

    def fake_analyze(**kwargs):
        captured.update(kwargs)
        return receipt_intelligence_client.ReceiptAnalysisResult(
            context=receipt_intelligence_client.ReceiptAnalysisContext(
                organization_ref="tenant-safe",
                report_ref="report-safe",
                item_ref="item-safe",
                attachment_ref="attachment-safe",
                event_id="00000000-0000-0000-0000-000000000001",
            ),
            analysis={
                "findings": [
                    {
                        "code": "duplicate_receipt_digest",
                        "severity": "warning",
                        "message": "The receipt may already have been used.",
                    }
                ],
                "ocr": {"performed": False},
            },
        )

    monkeypatch.setattr(receipt_intelligence_client, "analyze_receipt", fake_analyze)

    with _client_for_receipt_intelligence(engine, seeded_user) as client:
        response = client.post(
            f"/api/reports/{report.id}/items/{item.id}/receipt-analysis",
            json={"attachment_id": str(receipt.id)},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["advisory"] is True
    assert body["context"] == {
        "organization_ref": "tenant-safe",
        "report_ref": "report-safe",
        "item_ref": "item-safe",
        "attachment_ref": "attachment-safe",
        "event_id": "00000000-0000-0000-0000-000000000001",
    }
    assert body["analysis"]["ocr"]["performed"] is False
    assert body["analysis"]["findings"][0]["code"] == "duplicate_receipt_digest"

    assert set(captured) == {
        "organization_id",
        "report_id",
        "item_id",
        "attachment_id",
        "receipt_checksum",
        "receipt_mime_type",
        "receipt_size_bytes",
        "expense_amount",
        "currency",
        "receipt_required_at_or_above",
    }
    assert captured["organization_id"] == str(seeded_user.organization_id)
    assert captured["report_id"] == str(report.id)
    assert captured["item_id"] == str(item.id)
    assert captured["attachment_id"] == str(receipt.id)
    assert captured["receipt_checksum"] == "a" * 64
    assert captured["receipt_mime_type"] == "application/pdf"
    assert captured["receipt_size_bytes"] == 321
    assert captured["expense_amount"] == Decimal("75.50")
    assert captured["currency"] == "USD"
    assert captured["receipt_required_at_or_above"] == Decimal("25.00")

    forwarded = json.dumps(captured, default=str)
    assert "Private Merchant" not in forwarded
    assert "employee@example.com" not in forwarded
    assert "confidential-receipt.pdf" not in forwarded
    assert "description" not in forwarded


def test_receipt_analysis_rejects_an_attachment_from_a_different_item(
    engine,
    db,
    seeded_user,
    seeded_policy,
    seeded_category,
    monkeypatch,
):
    report, item, _receipt = _report_item_and_receipt(db, seeded_user, seeded_policy, seeded_category)
    other_item = ExpenseItem(
        expense_report_id=report.id,
        line_number=2,
        category_id=seeded_category.id,
        amount=Decimal("10.00"),
        original_amount=Decimal("10.00"),
        currency_code="USD",
        expense_date=date.today(),
    )
    db.add(other_item)
    db.flush()
    foreign_receipt = Attachment(
        entity_type="expense_item_receipt",
        entity_id=other_item.id,
        file_name="other.pdf",
        original_file_name="other.pdf",
        storage_path="local://test/other.pdf",
        mime_type="application/pdf",
        file_size_bytes=10,
        checksum="b" * 64,
        uploaded_by=seeded_user.id,
    )
    db.add(foreign_receipt)
    db.commit()
    monkeypatch.setattr(
        receipt_intelligence_client,
        "analyze_receipt",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("service must not be called")),
    )

    with _client_for_receipt_intelligence(engine, seeded_user) as client:
        response = client.post(
            f"/api/reports/{report.id}/items/{item.id}/receipt-analysis",
            json={"attachment_id": str(foreign_receipt.id)},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Receipt attachment not found"


def test_receipt_analysis_can_advisably_check_a_missing_receipt_against_its_threshold(
    engine,
    db,
    seeded_user,
    seeded_policy,
    seeded_category,
    monkeypatch,
):
    report, item, receipt = _report_item_and_receipt(db, seeded_user, seeded_policy, seeded_category)
    receipt.is_deleted = True
    db.commit()
    captured: dict[str, object] = {}

    def fake_analyze(**kwargs):
        captured.update(kwargs)
        return receipt_intelligence_client.ReceiptAnalysisResult(
            context=receipt_intelligence_client.ReceiptAnalysisContext(
                organization_ref="tenant-safe",
                report_ref="report-safe",
                item_ref="item-safe",
                attachment_ref=None,
                event_id="00000000-0000-0000-0000-000000000002",
            ),
            analysis={
                "findings": [
                    {"code": "receipt_required_missing", "severity": "warning"},
                ]
            },
        )

    monkeypatch.setattr(receipt_intelligence_client, "analyze_receipt", fake_analyze)

    with _client_for_receipt_intelligence(engine, seeded_user) as client:
        response = client.post(
            f"/api/reports/{report.id}/items/{item.id}/receipt-analysis",
            json={},
        )

    assert response.status_code == 200, response.text
    assert response.json()["context"]["attachment_ref"] is None
    assert captured["attachment_id"] is None
    assert captured["receipt_checksum"] is None
    assert captured["receipt_mime_type"] is None
    assert captured["receipt_size_bytes"] is None
    assert captured["receipt_required_at_or_above"] == Decimal("25.00")


def test_receipt_analysis_returns_safe_503_when_the_optional_service_is_unavailable(
    engine,
    db,
    seeded_user,
    seeded_policy,
    seeded_category,
    monkeypatch,
):
    report, item, _receipt = _report_item_and_receipt(db, seeded_user, seeded_policy, seeded_category)
    monkeypatch.setattr(
        receipt_intelligence_client,
        "analyze_receipt",
        lambda **_kwargs: (_ for _ in ()).throw(
            receipt_intelligence_client.ReceiptIntelligenceError("Receipt intelligence service is unavailable")
        ),
    )

    with _client_for_receipt_intelligence(engine, seeded_user) as client:
        response = client.post(
            f"/api/reports/{report.id}/items/{item.id}/receipt-analysis",
            json={},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "Receipt intelligence service is unavailable"
