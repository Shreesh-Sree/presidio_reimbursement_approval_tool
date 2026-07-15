"""Expense-report lifecycle and access rules.

The service owns report state transitions.  HTTP handlers only translate input
and domain errors, so employee and manager flows remain consistent whether
they are called from the web UI or an integration.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.approval_level import ApprovalLevel
from app.models.expense_item import ExpenseItem
from app.models.expense_report import ExpenseReport
from app.models.policy import Policy
from app.models.user import User
from app.services.audit_service import record_audit


EDITABLE_STATUSES = {"draft", "sent_back"}


class ReportError(ValueError):
    """A user-correctable report lifecycle error."""


class PolicyViolationError(ReportError):
    def __init__(self, violations: list[str]):
        self.violations = violations
        super().__init__("Report has policy violations")


def utcnow() -> datetime:
    return datetime.now(UTC)


def _as_uuid(value: uuid.UUID | str) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise ReportError("Invalid identifier") from exc


def _require_report(db: Session, report_id: uuid.UUID | str) -> ExpenseReport:
    report = (
        db.query(ExpenseReport)
        .filter(ExpenseReport.id == _as_uuid(report_id), ExpenseReport.is_deleted.is_(False))
        .first()
    )
    if not report:
        raise ReportError("Report not found")
    return report


def _require_owner(report: ExpenseReport, user_id: uuid.UUID | str) -> None:
    if report.employee_user_id != _as_uuid(user_id):
        raise ReportError("Only the report owner can perform this action")


def organization_id_for_report(db: Session, report: ExpenseReport) -> uuid.UUID:
    """Resolve the report owner's tenant before reading tenant-owned data."""

    employee = db.query(User).filter(User.id == report.employee_user_id, User.is_deleted.is_(False)).first()
    if employee is None:
        raise ReportError("Report employee no longer exists")
    return employee.organization_id


def _active_policy(
    db: Session,
    organization_id: uuid.UUID | str,
    at: datetime | None = None,
) -> Policy | None:
    at = at or utcnow()
    return (
        db.query(Policy)
        .filter(
            Policy.organization_id == _as_uuid(organization_id),
            Policy.is_active.is_(True),
            Policy.is_deleted.is_(False),
            Policy.effective_from <= at,
            (Policy.effective_to.is_(None) | (Policy.effective_to >= at)),
        )
        .order_by(Policy.effective_from.desc(), Policy.created_at.desc())
        .first()
    )


def create_draft(
    db: Session,
    employee_user_id: uuid.UUID | str,
    department_id: uuid.UUID | str,
    title: str,
    *,
    description: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    currency_code: str = "USD",
) -> ExpenseReport:
    if not title.strip():
        raise ReportError("A report title is required")
    if start_date and end_date and end_date < start_date:
        raise ReportError("End date cannot be before start date")

    employee_id = _as_uuid(employee_user_id)
    department_uuid = _as_uuid(department_id)
    report = ExpenseReport(
        report_number=f"RPT-{uuid.uuid4().hex[:12].upper()}",
        employee_user_id=employee_id,
        department_id=department_uuid,
        title=title.strip(),
        description=description.strip() if description else None,
        start_date=start_date,
        end_date=end_date,
        currency_code=currency_code.upper(),
        status="draft",
        total_amount=Decimal("0"),
        last_saved_at=utcnow(),
    )
    db.add(report)
    db.flush()
    record_audit(
        db,
        "expense_reports",
        str(report.id),
        "create",
        after={"status": report.status, "title": report.title},
        performed_by=str(employee_id),
    )
    db.commit()
    db.refresh(report)
    return report


def update_draft(
    db: Session,
    report_id: uuid.UUID | str,
    user_id: uuid.UUID | str,
    **changes: Any,
) -> ExpenseReport:
    report = _require_report(db, report_id)
    _require_owner(report, user_id)
    if report.status not in EDITABLE_STATUSES:
        raise ReportError("Only draft or sent-back reports can be edited")

    allowed = {"title", "description", "start_date", "end_date", "currency_code"}
    before = {field: str(getattr(report, field)) for field in allowed if field in changes}
    for field, value in changes.items():
        if field not in allowed or value is None:
            continue
        if field == "title":
            value = str(value).strip()
            if not value:
                raise ReportError("A report title is required")
        if field == "description" and isinstance(value, str):
            value = value.strip() or None
        if field == "currency_code":
            value = str(value).upper()
        setattr(report, field, value)
    if report.start_date and report.end_date and report.end_date < report.start_date:
        raise ReportError("End date cannot be before start date")
    report.last_saved_at = utcnow()
    record_audit(
        db,
        "expense_reports",
        str(report.id),
        "update",
        before=before,
        after={field: str(getattr(report, field)) for field in allowed if field in changes},
        performed_by=str(user_id),
    )
    db.commit()
    db.refresh(report)
    return report


def recompute_total(db: Session, report: ExpenseReport) -> Decimal:
    total = (
        db.query(func.coalesce(func.sum(ExpenseItem.amount), Decimal("0")))
        .filter(ExpenseItem.expense_report_id == report.id, ExpenseItem.is_deleted.is_(False))
        .scalar()
    )
    report.total_amount = Decimal(total or 0)
    return report.total_amount


def submit_report(db: Session, report_id: uuid.UUID | str, user_id: uuid.UUID | str) -> ExpenseReport:
    """Validate and submit a report while preserving its applied policy version."""

    report = _require_report(db, report_id)
    _require_owner(report, user_id)
    if report.status not in EDITABLE_STATUSES:
        raise ReportError("Only draft or sent-back reports can be submitted")

    items = (
        db.query(ExpenseItem)
        .filter(ExpenseItem.expense_report_id == report.id, ExpenseItem.is_deleted.is_(False))
        .order_by(ExpenseItem.line_number)
        .all()
    )
    if not items:
        raise ReportError("Add at least one expense item before submitting")

    policy = _active_policy(db, organization_id_for_report(db, report))
    if policy is None:
        raise ReportError("No active policy is available for submission")

    # Snapshot the policy version before evaluating it.  A subsequent policy
    # activation cannot silently reinterpret an already submitted claim.
    report.applied_policy_id = policy.id
    recompute_total(db, report)

    from app.services.validation_service import validate_report

    violations = validate_report(db, report, policy=policy)
    if violations:
        # Validation may persist line-item flags; keep the report editable and
        # persist those flags so the UI can explain exactly what needs fixing.
        db.commit()
        raise PolicyViolationError(violations)

    before = {"status": report.status, "applied_policy_id": str(report.applied_policy_id)}
    report.status = "submitted"
    report.submitted_at = utcnow()
    record_audit(
        db,
        "expense_reports",
        str(report.id),
        "submit",
        before=before,
        after={"status": report.status, "applied_policy_id": str(policy.id)},
        performed_by=str(user_id),
    )
    db.commit()
    db.refresh(report)
    return report


def withdraw_report(db: Session, report_id: uuid.UUID | str, user_id: uuid.UUID | str) -> ExpenseReport:
    report = _require_report(db, report_id)
    _require_owner(report, user_id)
    if report.status != "submitted":
        raise ReportError("Only submitted reports can be withdrawn")

    before = {"status": report.status}
    report.status = "draft"
    report.submitted_at = None
    # Cancel current tasks and stage manager notifications atomically with the
    # withdrawal. Outbound email is dispatched only after this commit.
    from app.services.notification_delivery_service import cancel_pending_approvals_for_withdrawal

    cancel_pending_approvals_for_withdrawal(db, report)
    record_audit(
        db,
        "expense_reports",
        str(report.id),
        "withdraw",
        before=before,
        after={"status": report.status},
        performed_by=str(user_id),
    )
    db.commit()
    db.refresh(report)
    return report


def list_reports(
    db: Session,
    organization_id: uuid.UUID | str | None = None,
    filters: dict[str, Any] | None = None,
    *,
    employee_user_id: uuid.UUID | str | None = None,
    status: str | None = None,
) -> list[ExpenseReport]:
    """List reports, retaining the legacy positional filter signature."""

    filters = filters or {}
    employee_user_id = employee_user_id or filters.get("employee_id")
    status = status or filters.get("status")
    query = db.query(ExpenseReport).filter(ExpenseReport.is_deleted.is_(False))
    if employee_user_id:
        query = query.filter(ExpenseReport.employee_user_id == _as_uuid(employee_user_id))
    if status:
        query = query.filter(ExpenseReport.status == status)
    return query.order_by(ExpenseReport.updated_at.desc()).all()


def get_report(db: Session, report_id: uuid.UUID | str) -> ExpenseReport | None:
    try:
        return _require_report(db, report_id)
    except (ReportError, ValueError):
        return None


def get_items(db: Session, report_id: uuid.UUID | str) -> list[ExpenseItem]:
    report = _require_report(db, report_id)
    return (
        db.query(ExpenseItem)
        .filter(ExpenseItem.expense_report_id == report.id, ExpenseItem.is_deleted.is_(False))
        .order_by(ExpenseItem.line_number)
        .all()
    )


def can_read_report(db: Session, report: ExpenseReport, actor: dict[str, Any]) -> bool:
    """Restrict reports to their owner, assigned approvers, and administrators."""

    try:
        actor_id = _as_uuid(actor["user_id"])
        actor_organization_id = _as_uuid(actor["organization_id"])
    except (KeyError, ReportError):
        return False
    # A role is scoped to its organization. Check tenant ownership before the
    # owner/admin/approval rules so a guessed report UUID never crosses a
    # tenant boundary.
    if organization_id_for_report(db, report) != actor_organization_id:
        return False
    if actor_id == report.employee_user_id:
        return True
    roles = {str(role).lower() for role in actor.get("roles", [])}
    if "administrator" in roles or "admin" in roles:
        return True
    if (
        db.query(ApprovalLevel.id)
        .filter(
            ApprovalLevel.expense_report_id == report.id,
            ApprovalLevel.approver_user_id == actor_id,
            ApprovalLevel.is_deleted.is_(False),
        )
        .first()
    ):
        return True
    return False


def employee_for_report(db: Session, report: ExpenseReport) -> User | None:
    return db.query(User).filter(User.id == report.employee_user_id).first()
