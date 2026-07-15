"""Core-to-AI boundary stays minimized and keeps AI state out of core tables."""

from __future__ import annotations

import json
import uuid
from datetime import date
from decimal import Decimal

from app.models.attachment import Attachment
from app.models.expense_item import ExpenseItem
from app.models.expense_report import ExpenseReport
from app.models.policy import PolicyRule
from app.models.vendor import Vendor
from app.services import ai_review_client
from app.services.report_service import create_draft


def _submitted_snapshot(db, seeded_user, seeded_policy, seeded_category):
    vendor = Vendor(name="Sensitive Merchant Name", normalized_name="SENSITIVE_VENDOR")
    db.add(vendor)
    db.flush()
    db.add(
        PolicyRule(
            policy_id=seeded_policy.id,
            category_id=seeded_category.id,
            max_per_trip=Decimal("500"),
            receipt_required_above=Decimal("25"),
        )
    )
    report = create_draft(db, seeded_user.id, seeded_user.department_id, "Client visit")
    report.applied_policy_id = seeded_policy.id
    item = ExpenseItem(
        expense_report_id=report.id,
        line_number=1,
        category_id=seeded_category.id,
        vendor_id=vendor.id,
        merchant_name="Sensitive Merchant Name",
        amount=Decimal("125"),
        original_amount=Decimal("125"),
        currency_code="USD",
        expense_date=date.today(),
        description="Contact employee@example.com for private customer details",
    )
    db.add(item)
    db.flush()
    db.add(
        Attachment(
            entity_type="expense_item_receipt",
            entity_id=item.id,
            file_name="receipt.pdf",
            original_file_name="receipt.pdf",
            storage_path="local://test/receipt.pdf",
            mime_type="application/pdf",
            file_size_bytes=10,
            checksum="a" * 64,
            uploaded_by=seeded_user.id,
        )
    )
    report.status = "submitted"
    db.commit()
    db.refresh(report)
    return report


def test_ai_event_excludes_personal_and_document_content(db, seeded_user, seeded_policy, seeded_category):
    report = _submitted_snapshot(db, seeded_user, seeded_policy, seeded_category)

    event = ai_review_client.build_review_event(db, report)
    serialized = json.dumps(event)

    assert event is not None
    assert event["items"][0]["category_code"] == "TRAVEL"
    assert event["items"][0]["vendor_code"] == "SENSITIVE_VENDOR"
    assert event["items"][0]["receipt"]["digest"].startswith("sha256:")
    assert "employee@example.com" not in serialized
    assert "Sensitive Merchant Name" not in serialized
    assert "receipt.pdf" not in serialized
    assert "description" not in serialized


def test_only_opaque_ai_job_reference_is_kept_on_report(db, seeded_user, seeded_policy, seeded_category, monkeypatch):
    report = _submitted_snapshot(db, seeded_user, seeded_policy, seeded_category)
    job_id = uuid.uuid4()
    monkeypatch.setenv("AI_REVIEW_SERVICE_URL", "http://ai-review.internal")
    monkeypatch.setattr(ai_review_client, "_request", lambda *_args, **_kwargs: {"id": str(job_id), "status": "queued"})

    queued = ai_review_client.request_review(db, report)

    assert queued == str(job_id)
    db.refresh(report)
    assert report.ai_review_job_id == job_id
    assert report.ai_review_requested_at is not None
