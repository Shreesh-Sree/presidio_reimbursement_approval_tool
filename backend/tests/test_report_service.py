
import pytest
from decimal import Decimal
from datetime import date
from app.services.report_service import create_draft, submit_report, withdraw_report
from app.models.expense_report import ExpenseReport
from app.models.expense_item import ExpenseItem


def add_valid_item(db, report, category):
    item = ExpenseItem(
        expense_report_id=report.id,
        line_number=1,
        category_id=category.id,
        amount=Decimal("10.00"),
        original_amount=Decimal("10.00"),
        currency_code="USD",
        expense_date=date.today(),
        description="Valid test expense",
    )
    db.add(item)
    db.commit()


def test_create_draft(db, seeded_user):
    report = create_draft(db, seeded_user.id, seeded_user.department_id, "Test Report")
    assert report.status == "draft"
    assert report.employee_user_id == seeded_user.id
    assert report.total_amount == Decimal("0")


def test_submit_report_sets_policy_snapshot(db, seeded_user, seeded_policy, seeded_category):
    report = create_draft(db, seeded_user.id, seeded_user.department_id, "Test")
    add_valid_item(db, report, seeded_category)
    submitted = submit_report(db, report.id, seeded_user.id)
    assert submitted.status == "submitted"
    assert submitted.applied_policy_id == seeded_policy.id
    assert submitted.submitted_at is not None


def test_withdraw_report_draft_to_submitted(db, seeded_user, seeded_policy, seeded_category):
    report = create_draft(db, seeded_user.id, seeded_user.department_id, "Test")
    add_valid_item(db, report, seeded_category)
    report = submit_report(db, report.id, seeded_user.id)
    withdrawn = withdraw_report(db, report.id, seeded_user.id)
    assert withdrawn.status == "draft"
