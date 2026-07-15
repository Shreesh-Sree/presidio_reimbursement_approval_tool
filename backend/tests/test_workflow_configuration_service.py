"""Configured workflow rules retain ordered multi-level approval behavior."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from app.models.expense_report import ExpenseReport
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.services import approval_service, user_service, workflow_service


def _approver(db, seeded_user, *, employee_number: str, email: str, full_name: str) -> User:
    user = User(
        organization_id=seeded_user.organization_id,
        department_id=seeded_user.department_id,
        employee_number=employee_number,
        username=email.split("@", 1)[0],
        email=email,
        password_hash=seeded_user.password_hash,
        full_name=full_name,
        status="active",
    )
    db.add(user)
    db.flush()
    return user


def _grant_approver_role(db, user: User) -> None:
    user_service.ensure_system_roles_and_permissions(db)
    approver_role = db.scalar(select(Role).where(Role.code == "approver"))
    assert approver_role is not None
    db.add(UserRole(user_id=user.id, role_id=approver_role.id))
    db.commit()


def test_configured_manager_and_named_approver_steps_create_ordered_levels(db, seeded_user):
    manager = _approver(
        db,
        seeded_user,
        employee_number="M-100",
        email="manager@example.com",
        full_name="Morgan Manager",
    )
    named_approver = _approver(
        db,
        seeded_user,
        employee_number="A-200",
        email="finance@example.com",
        full_name="Finley Finance",
    )
    _grant_approver_role(db, manager)
    _grant_approver_role(db, named_approver)
    seeded_user.manager_user_id = manager.id
    db.commit()

    rule = workflow_service.create_workflow_rule(
        db,
        organization_id=seeded_user.organization_id,
        actor_user_id=seeded_user.id,
        name="Escalate high-value reports",
        conditions={"min_total": "1000"},
        approval_chain=[{"manager_level": 1}, {"user_id": str(named_approver.id)}],
        priority=10,
    )
    report = ExpenseReport(
        report_number="RPT-WORKFLOW-1",
        employee_user_id=seeded_user.id,
        department_id=seeded_user.department_id,
        title="Client travel",
        currency_code="USD",
        total_amount=Decimal("1500.00"),
        status="submitted",
    )
    db.add(report)
    db.commit()

    levels = approval_service.init_workflow(db, report, seeded_user.id)

    assert report.workflow_rule_id == rule.id
    assert [(level.level_number, level.approver_user_id, level.status) for level in levels] == [
        (1, manager.id, "pending"),
        (2, named_approver.id, "waiting"),
    ]
