"""Delegated approvals preserve the original owner and human audit trail."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.approval_history import ApprovalHistory
from app.models.approval_level import ApprovalLevel
from app.models.expense_item import ExpenseItem
from app.models.user import User
from app.models.user_role import UserRole
from app.models.role import Role
from app.services import approval_service, delegation_service, user_service
from app.services.report_service import create_draft, submit_report


def _approver(db, seeded_user, *, employee_number: str, email: str, full_name: str, manager_id=None) -> User:
    user = User(
        organization_id=seeded_user.organization_id,
        department_id=seeded_user.department_id,
        employee_number=employee_number,
        username=email.split("@", 1)[0],
        email=email,
        password_hash=seeded_user.password_hash,
        full_name=full_name,
        manager_user_id=manager_id,
        status="active",
    )
    db.add(user)
    db.flush()
    user_service.ensure_system_roles_and_permissions(db)
    approver_role = db.scalar(select(Role).where(Role.code == "approver"))
    assert approver_role is not None
    db.add(UserRole(user_id=user.id, role_id=approver_role.id))
    db.commit()
    return user


def _submitted_report(db, seeded_user, seeded_category):
    report = create_draft(db, seeded_user.id, seeded_user.department_id, "Delegated client travel")
    db.add(
        ExpenseItem(
            expense_report_id=report.id,
            line_number=1,
            category_id=seeded_category.id,
            amount=Decimal("125.00"),
            original_amount=Decimal("125.00"),
            currency_code="USD",
            expense_date=date.today(),
            description="Client meeting travel",
        )
    )
    db.commit()
    return submit_report(db, report.id, seeded_user.id)


def test_active_approval_delegation_routes_the_task_and_records_the_original_owner(
    db,
    seeded_user,
    seeded_policy,
    seeded_category,
):
    manager = _approver(
        db,
        seeded_user,
        employee_number="M-DEL-1",
        email="manager.delegation@example.com",
        full_name="Morgan Manager",
    )
    delegate = _approver(
        db,
        seeded_user,
        employee_number="D-DEL-1",
        email="delegate.delegation@example.com",
        full_name="Devon Delegate",
    )
    seeded_user.manager_user_id = manager.id
    db.commit()

    now = datetime.now(UTC)
    delegation = delegation_service.create_delegation(
        db,
        delegator_user_id=manager.id,
        delegate_user_id=delegate.id,
        start_date=now - timedelta(hours=1),
        end_date=now + timedelta(days=2),
        scope="approval",
        remarks="Out of office",
    )
    report = _submitted_report(db, seeded_user, seeded_category)

    levels = approval_service.init_workflow(db, report, seeded_user.id)

    assert len(levels) == 1
    assert levels[0].approver_user_id == delegate.id
    assert levels[0].original_approver_user_id == manager.id
    assert levels[0].delegation_id == delegation.id
    assert approval_service.queue_for_approver(db, manager.id) == []
    assert approval_service.queue_for_approver(db, delegate.id)[0][1].id == report.id

    approved = approval_service.act_on_report(db, report.id, delegate.id, "approve", "Reviewed for manager")

    assert approved.status == "approved_pending_payment"
    history = (
        db.query(ApprovalHistory)
        .filter(ApprovalHistory.expense_report_id == report.id, ApprovalHistory.action == "approve")
        .one()
    )
    assert history.performed_by == delegate.id
    assert history.acting_for_user_id == manager.id


def test_creating_an_active_delegation_reassigns_an_already_pending_task(
    db,
    seeded_user,
    seeded_policy,
    seeded_category,
):
    manager = _approver(
        db,
        seeded_user,
        employee_number="M-DEL-PENDING",
        email="manager.pending.delegation@example.com",
        full_name="Morgan Pending Manager",
    )
    delegate = _approver(
        db,
        seeded_user,
        employee_number="D-DEL-PENDING",
        email="delegate.pending.delegation@example.com",
        full_name="Devon Pending Delegate",
    )
    seeded_user.manager_user_id = manager.id
    db.commit()

    report = _submitted_report(db, seeded_user, seeded_category)
    level = approval_service.init_workflow(db, report, seeded_user.id)[0]
    assert level.approver_user_id == manager.id

    delegation_service.create_delegation(
        db,
        delegator_user_id=manager.id,
        delegate_user_id=delegate.id,
        start_date=datetime.now(UTC) - timedelta(minutes=1),
        end_date=datetime.now(UTC) + timedelta(days=1),
    )

    db.refresh(level)
    assert level.approver_user_id == delegate.id
    assert level.original_approver_user_id == manager.id
    assert approval_service.queue_for_approver(db, manager.id) == []
    assert approval_service.queue_for_approver(db, delegate.id)[0][1].id == report.id


def test_cancelled_or_expired_delegation_revokes_a_pending_delegate(
    db,
    seeded_user,
    seeded_policy,
    seeded_category,
):
    manager = _approver(
        db,
        seeded_user,
        employee_number="M-DEL-REVOKE",
        email="manager.revoke.delegation@example.com",
        full_name="Morgan Revoking Manager",
    )
    delegate = _approver(
        db,
        seeded_user,
        employee_number="D-DEL-REVOKE",
        email="delegate.revoke.delegation@example.com",
        full_name="Devon Revoked Delegate",
    )
    seeded_user.manager_user_id = manager.id
    db.commit()

    now = datetime.now(UTC)
    delegation = delegation_service.create_delegation(
        db,
        delegator_user_id=manager.id,
        delegate_user_id=delegate.id,
        start_date=now - timedelta(minutes=1),
        end_date=now + timedelta(days=1),
    )
    report = _submitted_report(db, seeded_user, seeded_category)
    level = approval_service.init_workflow(db, report, seeded_user.id)[0]
    assert level.approver_user_id == delegate.id

    delegation_service.deactivate_delegation(db, delegation.id, actor_user_id=manager.id)
    db.refresh(level)
    assert level.approver_user_id == manager.id
    with pytest.raises(approval_service.ApprovalError):
        approval_service.act_on_report(db, report.id, delegate.id, "approve")
    assert approval_service.act_on_report(db, report.id, manager.id, "approve").status == "approved_pending_payment"

    # Expiry follows the same authorization path even if a stale record has
    # not yet been reconciled by the queue endpoint.
    second_report = _submitted_report(db, seeded_user, seeded_category)
    second_level = approval_service.init_workflow(db, second_report, seeded_user.id)[0]
    replacement = delegation_service.create_delegation(
        db,
        delegator_user_id=manager.id,
        delegate_user_id=delegate.id,
        start_date=datetime.now(UTC) - timedelta(minutes=1),
        end_date=datetime.now(UTC) + timedelta(days=1),
    )
    db.refresh(second_level)
    assert second_level.approver_user_id == delegate.id
    replacement.end_date = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()

    with pytest.raises(approval_service.ApprovalError):
        approval_service.act_on_report(db, second_report.id, delegate.id, "approve")
    db.refresh(second_level)
    assert second_level.approver_user_id == manager.id
    assert approval_service.queue_for_approver(db, manager.id)[0][1].id == second_report.id


def test_overdue_approval_escalates_to_the_next_eligible_manager(
    db,
    seeded_user,
    seeded_policy,
    seeded_category,
):
    director = _approver(
        db,
        seeded_user,
        employee_number="D-SLA-1",
        email="director.sla@example.com",
        full_name="Dara Director",
    )
    manager = _approver(
        db,
        seeded_user,
        employee_number="M-SLA-1",
        email="manager.sla@example.com",
        full_name="Morgan Manager",
        manager_id=director.id,
    )
    seeded_user.manager_user_id = manager.id
    db.commit()
    report = _submitted_report(db, seeded_user, seeded_category)
    level = approval_service.init_workflow(db, report, seeded_user.id)[0]
    overdue_at = datetime.now(UTC) - timedelta(minutes=1)
    level.due_at = overdue_at
    db.commit()

    escalated = approval_service.process_overdue_approvals(db, now=datetime.now(UTC))

    assert escalated == 1
    refreshed = db.get(ApprovalLevel, level.id)
    assert refreshed is not None
    assert refreshed.approver_user_id == director.id
    assert refreshed.original_approver_user_id == manager.id
    assert refreshed.escalated_at is not None
    assert approval_service.queue_for_approver(db, manager.id) == []
    assert approval_service.queue_for_approver(db, director.id)[0][1].id == report.id
    history = (
        db.query(ApprovalHistory)
        .filter(ApprovalHistory.expense_report_id == report.id, ApprovalHistory.action == "escalated")
        .one()
    )
    assert history.performed_by is None
    assert history.acting_for_user_id == manager.id


def test_overdue_approval_skips_a_non_approver_when_escalating_the_manager_chain(
    db,
    seeded_user,
    seeded_policy,
    seeded_category,
):
    director = _approver(
        db,
        seeded_user,
        employee_number="D-SLA-2",
        email="director.skip@example.com",
        full_name="Dara Director",
    )
    unavailable_manager = User(
        organization_id=seeded_user.organization_id,
        department_id=seeded_user.department_id,
        employee_number="M-SLA-NO-APPROVAL",
        username="manager-without-approval",
        email="manager.without.approval@example.com",
        password_hash=seeded_user.password_hash,
        full_name="Morgan Without Approval",
        manager_user_id=director.id,
        status="active",
    )
    db.add(unavailable_manager)
    db.flush()
    manager = _approver(
        db,
        seeded_user,
        employee_number="M-SLA-2",
        email="manager.skip@example.com",
        full_name="Morgan Manager",
        manager_id=unavailable_manager.id,
    )
    seeded_user.manager_user_id = manager.id
    db.commit()

    report = _submitted_report(db, seeded_user, seeded_category)
    level = approval_service.init_workflow(db, report, seeded_user.id)[0]
    level.due_at = datetime.now(UTC) - timedelta(minutes=1)
    db.commit()

    assert approval_service.process_overdue_approvals(db, now=datetime.now(UTC)) == 1
    refreshed = db.get(ApprovalLevel, level.id)
    assert refreshed is not None
    assert refreshed.approver_user_id == director.id
    assert refreshed.approver_user_id != unavailable_manager.id
