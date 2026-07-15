
import pytest
from decimal import Decimal
from app.services.report_service import create_draft, submit_report, withdraw_report
from app.models.expense_report import ExpenseReport


def test_create_draft(db, seeded_user):
    report = create_draft(db, seeded_user.id, seeded_user.department_id, "Test Report")
    assert report.status == "draft"
    assert report.employee_user_id == seeded_user.id
    assert report.total_amount == Decimal("0")


def test_submit_report_sets_policy_snapshot(db, seeded_user, seeded_policy):
    report = create_draft(db, seeded_user.id, seeded_user.department_id, "Test")
    submitted = submit_report(db, report.id, seeded_user.id)
    assert submitted.status == "submitted"
    assert submitted.applied_policy_id == seeded_policy.id
    assert submitted.submitted_at is not None


def test_withdraw_report_draft_to_submitted(db, seeded_user, seeded_policy):
    report = create_draft(db, seeded_user.id, seeded_user.department_id, "Test")
    report = submit_report(db, report.id, seeded_user.id)
    withdrawn = withdraw_report(db, report.id, seeded_user.id)
    assert withdrawn.status == "draft"
