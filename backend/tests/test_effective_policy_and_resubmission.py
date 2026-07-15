from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from app.models.expense_item import ExpenseItem
from app.models.user import User
from app.services import approval_service, policy_service
from app.services.report_service import create_draft, submit_report, withdraw_report


def _manager_for(db, employee):
    manager = User(
        organization_id=employee.organization_id,
        department_id=employee.department_id,
        employee_number="M-RESUBMIT",
        username="resubmit-manager",
        email="resubmit-manager@example.com",
        password_hash=employee.password_hash,
        full_name="Resubmission Manager",
        status="active",
    )
    db.add(manager)
    db.flush()
    employee.manager_user_id = manager.id
    db.commit()
    return manager


def _submitted_report(db, employee, category):
    report = create_draft(db, employee.id, employee.department_id, "Client travel")
    db.add(
        ExpenseItem(
            expense_report_id=report.id,
            line_number=1,
            category_id=category.id,
            amount=Decimal("25.00"),
            original_amount=Decimal("25.00"),
            currency_code="USD",
            expense_date=date.today(),
            description="Client transport",
        )
    )
    db.commit()
    return submit_report(db, report.id, employee.id)


def test_future_policy_activation_keeps_the_current_policy_usable(db):
    now = datetime.now(UTC)
    current = policy_service.create_policy_version(
        db,
        "Travel policy",
        "current",
        now - timedelta(days=1),
    )
    policy_service.activate_policy(db, current.id)
    future = policy_service.create_policy_version(
        db,
        "Travel policy",
        "next-quarter",
        now + timedelta(days=7),
    )

    policy_service.activate_policy(db, future.id)

    db.refresh(current)
    db.refresh(future)
    assert current.is_active is True
    assert future.is_active is True
    assert policy_service.get_active_policy(db).id == current.id


def test_sent_back_report_recreates_a_pending_manager_task_on_resubmission(
    db, seeded_user, seeded_policy, seeded_category
):
    manager = _manager_for(db, seeded_user)
    report = _submitted_report(db, seeded_user, seeded_category)
    approval_service.init_workflow(db, report, seeded_user.id)
    approval_service.act_on_report(db, report.id, manager.id, "send_back", "Please clarify the transport charge")

    resubmitted = submit_report(db, report.id, seeded_user.id)
    levels = approval_service.init_workflow(db, resubmitted, seeded_user.id)

    assert resubmitted.status == "submitted"
    assert levels[0].approver_user_id == manager.id
    assert levels[0].status == "pending"
    assert approval_service.queue_for_approver(db, manager.id)[0][1].id == report.id


def test_withdrawn_report_recreates_a_pending_manager_task_on_resubmission(
    db, seeded_user, seeded_policy, seeded_category
):
    manager = _manager_for(db, seeded_user)
    report = _submitted_report(db, seeded_user, seeded_category)
    approval_service.init_workflow(db, report, seeded_user.id)
    withdraw_report(db, report.id, seeded_user.id)

    resubmitted = submit_report(db, report.id, seeded_user.id)
    levels = approval_service.init_workflow(db, resubmitted, seeded_user.id)

    assert levels[0].approver_user_id == manager.id
    assert levels[0].status == "pending"
    assert approval_service.queue_for_approver(db, manager.id)[0][1].id == report.id
