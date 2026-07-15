from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.models.expense_item import ExpenseItem
from app.models.user import User
from app.services import approval_service
from app.services.report_service import create_draft, submit_report


def test_manager_can_list_their_completed_report_history(db, seeded_user, seeded_policy, seeded_category):
    manager = User(
        organization_id=seeded_user.organization_id,
        department_id=seeded_user.department_id,
        employee_number="M-HISTORY",
        username="history-manager",
        email="history-manager@example.com",
        password_hash=seeded_user.password_hash,
        full_name="History Manager",
        status="active",
    )
    db.add(manager)
    db.flush()
    seeded_user.manager_user_id = manager.id
    report = create_draft(db, seeded_user.id, seeded_user.department_id, "Customer visit")
    db.add(
        ExpenseItem(
            expense_report_id=report.id,
            line_number=1,
            category_id=seeded_category.id,
            amount=Decimal("25.00"),
            original_amount=Decimal("25.00"),
            currency_code="USD",
            expense_date=date.today(),
            description="Customer transport",
        )
    )
    db.commit()
    submitted = submit_report(db, report.id, seeded_user.id)
    approval_service.init_workflow(db, submitted, seeded_user.id)
    approval_service.act_on_report(db, report.id, manager.id, "approve")

    history = approval_service.history_for_approver(db, manager.id)

    assert len(history) == 1
    level, history_report = history[0]
    assert history_report.id == report.id
    assert level.status == "approved"
