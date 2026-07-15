from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.models.approval_level import ApprovalLevel
from app.models.expense_item import ExpenseItem
from app.models.notification import Notification
from app.models.user import User
from app.services import approval_service
from app.services.report_service import create_draft, submit_report, withdraw_report


def test_withdrawal_cancels_manager_task_and_notifies_manager(
    db, seeded_user, seeded_policy, seeded_category
):
    manager = User(
        organization_id=seeded_user.organization_id,
        department_id=seeded_user.department_id,
        employee_number="M-WITHDRAW",
        username="withdraw-manager",
        email="withdraw-manager@example.com",
        password_hash=seeded_user.password_hash,
        full_name="Withdrawal Manager",
        status="active",
    )
    db.add(manager)
    db.flush()
    seeded_user.manager_user_id = manager.id
    report = create_draft(db, seeded_user.id, seeded_user.department_id, "Client travel")
    db.add(
        ExpenseItem(
            expense_report_id=report.id,
            line_number=1,
            category_id=seeded_category.id,
            amount=Decimal("20.00"),
            original_amount=Decimal("20.00"),
            currency_code="USD",
            expense_date=date.today(),
            description="Client transport",
        )
    )
    db.commit()
    submitted = submit_report(db, report.id, seeded_user.id)
    approval_service.init_workflow(db, submitted, seeded_user.id)

    withdrawn = withdraw_report(db, report.id, seeded_user.id)

    assert withdrawn.status == "draft"
    level = db.query(ApprovalLevel).filter(ApprovalLevel.expense_report_id == report.id).one()
    assert level.status == "cancelled"
    notifications = (
        db.query(Notification)
        .filter(
            Notification.recipient_user_id == manager.id,
            Notification.template_code == "report_withdrawn",
        )
        .all()
    )
    assert {notification.channel for notification in notifications} == {"in_app", "email"}
