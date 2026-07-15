"""Multi-level, human-in-the-loop expense approval workflow."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.approval_history import ApprovalHistory
from app.models.approval_level import ApprovalLevel
from app.models.expense_report import ExpenseReport
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.models.workflow_rule import WorkflowRule
from app.services.audit_service import record_audit
from app.services import delegation_service
from app.services.notification_service import notify
from app.services.report_service import ReportError, _as_uuid, _require_report


class ApprovalError(ReportError):
    """A user-correctable approval workflow error."""


def utcnow() -> datetime:
    return datetime.now(UTC)


def _active_manager_chain(db: Session, employee: User) -> list[User]:
    chain: list[User] = []
    seen = {employee.id}
    manager_id = employee.manager_user_id
    while manager_id:
        if manager_id in seen:
            raise ApprovalError("The employee reporting hierarchy contains a cycle")
        seen.add(manager_id)
        manager = (
            db.query(User)
            .filter(User.id == manager_id, User.is_deleted.is_(False), User.status == "active")
            .first()
        )
        if manager is None:
            break
        chain.append(manager)
        manager_id = manager.manager_user_id
    return chain


def _rule_matches(
    rule: WorkflowRule,
    report: ExpenseReport,
    organization_id: uuid.UUID | None = None,
) -> bool:
    conditions = rule.conditions_json or {}
    configured_organization_id = conditions.get("organization_id")
    if configured_organization_id and (
        organization_id is None or str(configured_organization_id) != str(organization_id)
    ):
        return False
    total = Decimal(report.total_amount or 0)
    try:
        if "min_total" in conditions and total < Decimal(str(conditions["min_total"])):
            return False
        if "max_total" in conditions and total > Decimal(str(conditions["max_total"])):
            return False
    except (ArithmeticError, ValueError):
        return False
    department_id = conditions.get("department_id")
    if department_id and str(report.department_id) != str(department_id):
        return False
    currency_code = conditions.get("currency_code")
    if currency_code and report.currency_code.upper() != str(currency_code).upper():
        return False
    return True


def _matching_rule(
    db: Session,
    report: ExpenseReport,
    organization_id: uuid.UUID | None = None,
) -> WorkflowRule | None:
    rules = (
        db.query(WorkflowRule)
        .filter(WorkflowRule.is_active.is_(True), WorkflowRule.is_deleted.is_(False))
        .order_by(WorkflowRule.priority.asc(), WorkflowRule.created_at.asc())
        .all()
    )
    return next((rule for rule in rules if _rule_matches(rule, report, organization_id)), None)


def _users_for_role(db: Session, role_code: str, organization_id) -> list[User]:
    return (
        db.query(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .filter(
            User.organization_id == organization_id,
            User.is_deleted.is_(False),
            User.status == "active",
            UserRole.is_deleted.is_(False),
            Role.is_deleted.is_(False),
            Role.is_active.is_(True),
            Role.code == role_code.lower(),
        )
        .order_by(User.full_name)
        .all()
    )


def _approvers_for_report(db: Session, report: ExpenseReport) -> tuple[WorkflowRule | None, list[User]]:
    employee = db.query(User).filter(User.id == report.employee_user_id).first()
    if not employee:
        raise ApprovalError("Report employee no longer exists")
    managers = _active_manager_chain(db, employee)
    rule = _matching_rule(db, report, employee.organization_id)
    selected: list[User] = []
    if rule:
        for step in rule.approval_chain_json or []:
            if not isinstance(step, dict):
                continue
            if step.get("manager_level") is not None:
                try:
                    index = int(step["manager_level"]) - 1
                except (TypeError, ValueError):
                    continue
                if 0 <= index < len(managers):
                    selected.append(managers[index])
            elif step.get("user_id"):
                try:
                    user_id = _as_uuid(step["user_id"])
                except ValueError:
                    continue
                user = (
                    db.query(User)
                    .filter(
                        User.id == user_id,
                        User.organization_id == employee.organization_id,
                        User.is_deleted.is_(False),
                        User.status == "active",
                    )
                    .first()
                )
                if user:
                    selected.append(user)
            elif step.get("role_code"):
                selected.extend(_users_for_role(db, str(step["role_code"]), employee.organization_id))
    if not selected and managers:
        selected = [managers[0]]

    unique: list[User] = []
    seen: set[uuid.UUID] = set()
    for user in selected:
        if user.id != employee.id and user.id not in seen:
            unique.append(user)
            seen.add(user.id)
    if not unique:
        raise ApprovalError("This employee does not have an active reporting manager")
    return rule, unique


def validate_workflow_for_report(db: Session, report: ExpenseReport) -> None:
    """Fail before submission if no valid human approver can be assigned."""

    _approvers_for_report(db, report)


def _assign_current_delegate(
    db: Session,
    level: ApprovalLevel,
    original_approver_id: uuid.UUID,
    *,
    at: datetime | None = None,
) -> None:
    """Keep an approval's original owner while assigning any active delegate."""

    assignee_id, delegation = delegation_service.resolve_approval_assignee(db, original_approver_id, at=at)
    level.original_approver_user_id = original_approver_id
    level.approver_user_id = assignee_id
    level.delegation_id = delegation.id if delegation else None


def _synchronize_pending_delegation_assignment(
    db: Session,
    level: ApprovalLevel,
    *,
    at: datetime | None = None,
    performed_by: uuid.UUID | str | None = None,
) -> bool:
    """Revoke stale delegation access without undoing an SLA escalation.

    A pending task may outlive a temporary delegation.  The approval level is
    the authorization source of truth, so it must be reconciled before a
    queue is displayed or a decision is accepted.  Escalations intentionally
    keep their new human assignee even if the original delegation later ends.
    """

    if level.status != "pending" or level.escalated_at is not None:
        return False

    original_approver_id = level.original_approver_user_id or level.approver_user_id
    before = {
        "approver_user_id": str(level.approver_user_id),
        "delegation_id": str(level.delegation_id) if level.delegation_id else None,
    }
    _assign_current_delegate(db, level, original_approver_id, at=at)
    after = {
        "approver_user_id": str(level.approver_user_id),
        "delegation_id": str(level.delegation_id) if level.delegation_id else None,
    }
    if before == after:
        return False

    record_audit(
        db,
        "approval_levels",
        str(level.id),
        "delegation_assignment_reconciled",
        before=before,
        after=after,
        performed_by=str(performed_by) if performed_by else None,
    )
    return True


def synchronize_pending_delegations(
    db: Session,
    *,
    user_id: uuid.UUID | str | None = None,
    at: datetime | None = None,
    performed_by: uuid.UUID | str | None = None,
) -> list[tuple[ApprovalLevel, ExpenseReport, uuid.UUID]]:
    """Reconcile currently actionable tasks for one approver or the whole queue.

    The caller owns the transaction.  Returned rows include the prior assignee
    so callers can atomically persist notifications alongside the reassignment.
    """

    query = (
        db.query(ApprovalLevel, ExpenseReport)
        .join(ExpenseReport, ExpenseReport.id == ApprovalLevel.expense_report_id)
        .filter(
            ApprovalLevel.status == "pending",
            ApprovalLevel.escalated_at.is_(None),
            ApprovalLevel.is_deleted.is_(False),
            ExpenseReport.is_deleted.is_(False),
            ExpenseReport.status == "submitted",
        )
    )
    if user_id is not None:
        approver_id = _as_uuid(user_id)
        query = query.filter(
            or_(
                ApprovalLevel.approver_user_id == approver_id,
                ApprovalLevel.original_approver_user_id == approver_id,
            )
        )

    changes: list[tuple[ApprovalLevel, ExpenseReport, uuid.UUID]] = []
    for level, report in query.with_for_update().all():
        previous_assignee_id = level.approver_user_id
        if not _synchronize_pending_delegation_assignment(
            db,
            level,
            at=at,
            performed_by=performed_by,
        ):
            continue
        changes.append((level, report, previous_assignee_id))
        notify(
            db,
            level.approver_user_id,
            "approval_assignment_updated",
            {
                "title": "Expense report awaiting your approval",
                "body": f"{report.title} is now assigned to you for review.",
                "report_id": str(report.id),
                "type": "approval_request",
            },
            channels=("in_app", "email"),
        )
    return changes


def _due_at(now: datetime | None = None) -> datetime:
    return (now or utcnow()) + timedelta(hours=get_settings().approval_sla_hours)


def _active_escalation_manager(db: Session, original_approver_user_id: uuid.UUID) -> User | None:
    """Return the next eligible human manager, never a guessed replacement."""

    original = (
        db.query(User)
        .filter(
            User.id == original_approver_user_id,
            User.is_deleted.is_(False),
            User.status == "active",
        )
        .first()
    )
    if original is None:
        return None
    candidate_id = original.manager_user_id
    seen = {original.id}
    while candidate_id and candidate_id not in seen:
        seen.add(candidate_id)
        manager = (
            db.query(User)
            .filter(
                User.id == candidate_id,
                User.organization_id == original.organization_id,
                User.is_deleted.is_(False),
                User.status == "active",
            )
            .first()
        )
        if manager is None:
            return None
        if delegation_service.is_approval_eligible(db, manager.id):
            return manager
        candidate_id = manager.manager_user_id
    return None


def init_workflow(db: Session, report: ExpenseReport, submitted_by: uuid.UUID | str | None = None) -> list[ApprovalLevel]:
    """Create sequential approver tasks when a report enters ``submitted``."""

    if report.status != "submitted":
        raise ApprovalError("Only submitted reports can enter approval")
    existing_levels = (
        db.query(ApprovalLevel)
        .filter(ApprovalLevel.expense_report_id == report.id, ApprovalLevel.is_deleted.is_(False))
        .order_by(ApprovalLevel.level_number)
        .all()
    )
    # Idempotent calls during the same submission must not duplicate a live
    # task.  Terminal/cancelled rows, however, belong to an earlier round and
    # must be re-opened when an employee resubmits after a withdrawal/send-back.
    if any(level.status in {"pending", "waiting"} for level in existing_levels):
        return existing_levels

    rule, approvers = _approvers_for_report(db, report)
    report.workflow_rule_id = rule.id if rule else None
    existing_by_assignment = {
        (level.level_number, level.original_approver_user_id or level.approver_user_id): level
        for level in existing_levels
    }
    levels: list[ApprovalLevel] = []
    workflow_started_at = utcnow()
    for number, approver in enumerate(approvers, start=1):
        assignment = (number, approver.id)
        level = existing_by_assignment.get(assignment)
        if level is None:
            level = ApprovalLevel(
                expense_report_id=report.id,
                approver_user_id=approver.id,
                original_approver_user_id=approver.id,
                level_number=number,
            )
            db.add(level)
        _assign_current_delegate(db, level, approver.id)
        level.status = "pending" if number == 1 else "waiting"
        level.decision_date = None
        level.due_at = _due_at(workflow_started_at) if number == 1 else None
        level.reminder_sent_at = None
        level.escalated_at = None
        level.remarks = None
        levels.append(level)

    active_assignments = {
        (level.level_number, level.original_approver_user_id or level.approver_user_id)
        for level in levels
    }
    for previous in existing_levels:
        original_approver_id = previous.original_approver_user_id or previous.approver_user_id
        if (previous.level_number, original_approver_id) not in active_assignments:
            previous.status = "cancelled"

    db.flush()
    actor_id = _as_uuid(submitted_by) if submitted_by else report.employee_user_id
    db.add(
        ApprovalHistory(
            expense_report_id=report.id,
            action="resubmitted" if existing_levels else "submitted",
            performed_by=actor_id,
        )
    )
    notify(
        db,
        levels[0].approver_user_id,
        "report_submitted_for_approval",
        {
            "title": "Expense report awaiting your approval",
            "body": f"{report.title} has been submitted for your review.",
            "report_id": str(report.id),
            "type": "approval_request",
        },
        channels=("in_app", "email"),
    )
    record_audit(
        db,
        "expense_reports",
        str(report.id),
        "workflow_restarted" if existing_levels else "workflow_started",
        after={
            "approver_count": len(levels),
            "delegated_level_count": sum(level.delegation_id is not None for level in levels),
            "workflow_rule_id": str(rule.id) if rule else None,
        },
        performed_by=str(actor_id),
    )
    db.commit()
    for level in levels:
        db.refresh(level)
    return levels


def queue_for_approver(db: Session, user_id: uuid.UUID | str) -> list[tuple[ApprovalLevel, ExpenseReport]]:
    approver_id = _as_uuid(user_id)
    # Time is part of a delegation's authorization boundary. Reconcile both
    # the original owner and a possible delegate before exposing this queue.
    if synchronize_pending_delegations(db, user_id=approver_id):
        db.commit()
    return (
        db.query(ApprovalLevel, ExpenseReport)
        .join(ExpenseReport, ExpenseReport.id == ApprovalLevel.expense_report_id)
        .filter(
            ApprovalLevel.approver_user_id == approver_id,
            ApprovalLevel.status == "pending",
            ApprovalLevel.is_deleted.is_(False),
            ExpenseReport.is_deleted.is_(False),
            ExpenseReport.status == "submitted",
        )
        .order_by(ExpenseReport.submitted_at.asc())
        .all()
    )


def history_for_approver(db: Session, user_id: uuid.UUID | str) -> list[tuple[ApprovalLevel, ExpenseReport]]:
    """Return completed/cancelled decisions for an approver's team history."""

    approver_id = _as_uuid(user_id)
    return (
        db.query(ApprovalLevel, ExpenseReport)
        .join(ExpenseReport, ExpenseReport.id == ApprovalLevel.expense_report_id)
        .filter(
            ApprovalLevel.approver_user_id == approver_id,
            ApprovalLevel.status.notin_(("pending", "waiting")),
            ApprovalLevel.is_deleted.is_(False),
            ExpenseReport.is_deleted.is_(False),
        )
        .order_by(ApprovalLevel.decision_date.desc(), ExpenseReport.updated_at.desc())
        .all()
    )


def _pending_level(db: Session, report: ExpenseReport, user_id: uuid.UUID | str) -> ApprovalLevel:
    actor_id = _as_uuid(user_id)
    level = (
        db.query(ApprovalLevel)
        .filter(
            ApprovalLevel.expense_report_id == report.id,
            ApprovalLevel.status == "pending",
            ApprovalLevel.is_deleted.is_(False),
        )
        .with_for_update()
        .first()
    )
    if level is None:
        raise ApprovalError("This report is not awaiting your approval")
    changed = _synchronize_pending_delegation_assignment(db, level)
    if level.approver_user_id != actor_id:
        # Persist a time-based revocation before rejecting a former delegate.
        # Normal decisions retain the assignment change in their transaction.
        if changed:
            db.commit()
        raise ApprovalError("This report is not awaiting your approval")
    return level


def act_on_report(
    db: Session,
    report_id: uuid.UUID | str,
    user_id: uuid.UUID | str,
    action: str,
    remarks: str | None = None,
) -> ExpenseReport:
    if action not in {"approve", "reject", "send_back"}:
        raise ApprovalError("Unsupported approval action")
    if action in {"reject", "send_back"} and not (remarks or "").strip():
        raise ApprovalError("Remarks are required for rejection or send-back")

    report = _require_report(db, report_id)
    if report.status != "submitted":
        raise ApprovalError("Only submitted reports can be actioned")
    level = _pending_level(db, report, user_id)
    level.status = "approved" if action == "approve" else action
    level.decision_date = utcnow()
    level.remarks = (remarks or "").strip() or None
    db.add(
        ApprovalHistory(
            expense_report_id=report.id,
            approval_level_id=level.id,
            action=action,
            performed_by=_as_uuid(user_id),
            acting_for_user_id=(
                level.original_approver_user_id
                if level.original_approver_user_id and level.original_approver_user_id != _as_uuid(user_id)
                else None
            ),
            remarks=level.remarks,
        )
    )

    if action == "approve":
        next_level = (
            db.query(ApprovalLevel)
            .filter(
                ApprovalLevel.expense_report_id == report.id,
                ApprovalLevel.status == "waiting",
                ApprovalLevel.is_deleted.is_(False),
            )
            .order_by(ApprovalLevel.level_number)
            .first()
        )
        if next_level:
            original_approver_id = next_level.original_approver_user_id or next_level.approver_user_id
            _assign_current_delegate(db, next_level, original_approver_id)
            next_level.status = "pending"
            next_level.due_at = _due_at()
            next_level.reminder_sent_at = None
            next_level.escalated_at = None
            notify(
                db,
                next_level.approver_user_id,
                "report_escalated_for_approval",
                {
                    "title": "Expense report awaiting your approval",
                    "body": f"{report.title} advanced to your approval level.",
                    "report_id": str(report.id),
                    "type": "approval_request",
                },
                channels=("in_app", "email"),
            )
        else:
            report.status = "approved_pending_payment"
            # Finance state is created inside this same transaction so a
            # completed approval never leaves a report without a payment row.
            from app.services.payment_service import ensure_pending_payment

            ensure_pending_payment(db, report, created_by=user_id)
            notify(
                db,
                report.employee_user_id,
                "report_approved_pending_payment",
                {
                    "title": "Expense report approved",
                    "body": f"{report.title} is approved and pending payment.",
                    "report_id": str(report.id),
                    "type": "report_status",
                },
                channels=("in_app", "email"),
            )
    else:
        report.status = "rejected" if action == "reject" else "sent_back"
        (
            db.query(ApprovalLevel)
            .filter(
                ApprovalLevel.expense_report_id == report.id,
                ApprovalLevel.status.in_(("pending", "waiting")),
                ApprovalLevel.is_deleted.is_(False),
            )
            .update({"status": "cancelled"}, synchronize_session=False)
        )
        notify(
            db,
            report.employee_user_id,
            "report_rejected" if action == "reject" else "report_sent_back",
            {
                "title": "Expense report rejected" if action == "reject" else "Expense report sent back",
                "body": level.remarks or f"{report.title} needs your attention.",
                "report_id": str(report.id),
                "type": "report_status",
            },
            channels=("in_app", "email"),
        )

    record_audit(
        db,
        "expense_reports",
        str(report.id),
        action,
        after={"status": report.status, "approval_level": level.level_number},
        performed_by=str(user_id),
    )
    db.commit()
    db.refresh(report)
    return report


def process_overdue_approvals(
    db: Session,
    *,
    organization_id: uuid.UUID | str | None = None,
    now: datetime | None = None,
) -> int:
    """Escalate overdue tasks once to an eligible manager, never auto-decide.

    This function is idempotent and may be called by an internal scheduler or
    a safe read-path sweep. If no eligible next manager exists, it sends one
    reminder to the current human assignee and leaves the task pending.
    """

    moment = now or utcnow()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    query = (
        db.query(ApprovalLevel, ExpenseReport, User)
        .join(ExpenseReport, ExpenseReport.id == ApprovalLevel.expense_report_id)
        .join(User, User.id == ExpenseReport.employee_user_id)
        .filter(
            ApprovalLevel.status == "pending",
            ApprovalLevel.due_at.is_not(None),
            ApprovalLevel.due_at <= moment,
            ApprovalLevel.escalated_at.is_(None),
            ApprovalLevel.is_deleted.is_(False),
            ExpenseReport.is_deleted.is_(False),
            ExpenseReport.status == "submitted",
            User.is_deleted.is_(False),
        )
    )
    if organization_id is not None:
        organization_uuid = _as_uuid(organization_id)
        query = query.filter(User.organization_id == organization_uuid)

    escalated_count = 0
    changed = bool(synchronize_pending_delegations(db, at=moment))
    for level, report, _employee in query.with_for_update().all():
        original_approver_id = level.original_approver_user_id or level.approver_user_id
        escalation_manager = _active_escalation_manager(db, original_approver_id)
        if escalation_manager is None:
            if level.reminder_sent_at is None:
                level.reminder_sent_at = moment
                changed = True
                notify(
                    db,
                    level.approver_user_id,
                    "approval_sla_reminder",
                    {
                        "title": "Approval reminder",
                        "body": f"{report.title} is past its approval target and still needs your decision.",
                        "report_id": str(report.id),
                        "type": "approval_request",
                    },
                    channels=("in_app", "email"),
                )
            continue

        previous_assignee_id = level.approver_user_id
        previous_due_at = level.due_at
        level.approver_user_id = escalation_manager.id
        level.escalated_at = moment
        level.reminder_sent_at = moment
        # A fresh SLA applies to the escalation recipient. The original owner
        # and any initial delegation remain stored as provenance on the level.
        level.due_at = _due_at(moment)
        db.add(
            ApprovalHistory(
                expense_report_id=report.id,
                approval_level_id=level.id,
                action="escalated",
                performed_by=None,
                acting_for_user_id=original_approver_id,
                remarks="Automatically escalated after the approval SLA elapsed.",
            )
        )
        notify(
            db,
            escalation_manager.id,
            "report_escalated_for_approval",
            {
                "title": "Expense report escalated for your approval",
                "body": f"{report.title} is overdue at a lower approval level.",
                "report_id": str(report.id),
                "type": "approval_request",
            },
            channels=("in_app", "email"),
        )
        record_audit(
            db,
            "approval_levels",
            str(level.id),
            "sla_escalated",
            before={"approver_user_id": str(previous_assignee_id), "due_at": str(previous_due_at)},
            after={"approver_user_id": str(escalation_manager.id), "original_approver_user_id": str(original_approver_id)},
        )
        escalated_count += 1
        changed = True
    if changed:
        db.commit()
    return escalated_count


def approval_history_for_report(db: Session, report_id: uuid.UUID | str) -> list[ApprovalHistory]:
    return (
        db.query(ApprovalHistory)
        .filter(
            ApprovalHistory.expense_report_id == _as_uuid(report_id),
            ApprovalHistory.is_deleted.is_(False),
        )
        .order_by(ApprovalHistory.performed_at, ApprovalHistory.created_at)
        .all()
    )
