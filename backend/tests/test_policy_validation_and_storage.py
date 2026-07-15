from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.models.expense_item import ExpenseItem
from app.models.expense_report import ExpenseReport
from app.services import category_service, policy_service, storage_service, validation_service


def _draft_report(db, seeded_user, *, policy_id=None) -> ExpenseReport:
    report = ExpenseReport(
        report_number="RPT-POLICY-1",
        employee_user_id=seeded_user.id,
        department_id=seeded_user.department_id,
        applied_policy_id=policy_id,
        title="Client travel",
        status="draft",
        total_amount=Decimal("0"),
    )
    db.add(report)
    db.flush()
    return report


def test_policy_version_creates_rules_and_preserves_effective_window(db):
    policy = policy_service.create_policy_version(
        db,
        "Travel Policy",
        "v2",
        date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
        rules_data=[
            {
                "category_name": "Travel",
                "vendor_name": "Acme Taxi",
                "max_per_day": "125.00",
                "receipt_required_above": "20.00",
            }
        ],
    )

    assert policy.is_active is False
    assert len(policy.rules) == 1
    payload = policy_service.policy_payload(db, policy)
    assert payload["effective_to"].startswith("2026-12-31")
    assert payload["rules"][0]["category_name"] == "Travel"
    assert payload["rules"][0]["vendor_name"] == "Acme Taxi"

    active = policy_service.activate_policy(db, policy.id)
    assert active.is_active is True
    with pytest.raises(policy_service.PolicyConflictError):
        policy_service.update_policy_version(db, active.id, name="Changed in place")


def test_category_hierarchy_rejects_deleting_a_parent_with_active_children(db):
    parent = category_service.create_category(db, "TRAVEL", "Travel")
    child = category_service.create_category(db, "AIR", "Airfare", parent_id=parent.id)

    tree = category_service.category_tree_payload(category_service.list_categories(db))
    assert tree[0]["id"] == str(parent.id)
    assert tree[0]["children"][0]["id"] == str(child.id)
    with pytest.raises(category_service.CategoryConflictError):
        category_service.deactivate_category(db, parent.id)


def test_validation_uses_policy_rules_and_does_not_change_report_status(db, seeded_user):
    policy = policy_service.create_policy_version(
        db,
        "Travel Policy",
        "v3",
        date(2026, 1, 1),
        rules_data=[
            {
                "category_name": "Meals",
                "per_category_cap": "50.00",
                "receipt_required_above": "25.00",
            }
        ],
    )
    category_id = policy.rules[0].category_id
    report = _draft_report(db, seeded_user, policy_id=policy.id)
    item = ExpenseItem(
        expense_report_id=report.id,
        line_number=1,
        category_id=category_id,
        amount=Decimal("60.00"),
        currency_code="USD",
        expense_date=date(2026, 2, 1),
        description="Dinner with client",
    )
    db.add(item)
    db.flush()

    violations = validation_service.validate_report(db, report)

    assert report.status == "draft"
    assert item.is_policy_violated is True
    assert "Category total" in item.policy_violation_reason
    assert "receipt is required" in item.policy_violation_reason
    assert violations[0].startswith("Line 1:")


def test_receipt_storage_validates_metadata_and_returns_local_file(db, seeded_user, tmp_path, monkeypatch):
    monkeypatch.setenv("LOCAL_STORAGE_PATH", str(tmp_path / "uploads"))
    report = _draft_report(db, seeded_user)
    category = category_service.create_category(db, "LODGING", "Lodging")
    item = ExpenseItem(
        expense_report_id=report.id,
        line_number=1,
        category_id=category.id,
        amount=Decimal("10.00"),
        currency_code="USD",
        expense_date=date(2026, 2, 1),
        description="Hotel tax",
    )
    db.add(item)
    db.flush()

    attachment = storage_service.create_attachment(
        db,
        entity_type="expense_item_receipt",
        entity_id=item.id,
        uploaded_by=seeded_user.id,
        file_name="receipt.pdf",
        mime_type="application/pdf",
        content=b"%PDF-test-receipt",
        kind="receipt",
    )
    db.commit()

    assert storage_service.read_attachment(attachment) == b"%PDF-test-receipt"
    assert storage_service.attachment_payload(attachment)["url"].endswith(f"/{attachment.id}/download")
    with pytest.raises(storage_service.UploadValidationError):
        storage_service.validate_upload("receipt", "receipt.pdf", "image/png", b"not-a-pdf")
