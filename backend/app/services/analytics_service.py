"""Role-scoped, aggregate reporting insights.

The analytics boundary intentionally returns counts and monetary aggregates only.
It never includes employee names, emails, receipt references, descriptions, or
AI findings.  This keeps an administrator dashboard useful without creating a
second employee-profiling data surface.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.approval_history import ApprovalHistory
from app.models.approval_level import ApprovalLevel
from app.models.expense_category import ExpenseCategory
from app.models.expense_item import ExpenseItem
from app.models.expense_report import ExpenseReport
from app.models.user import User


class AnalyticsError(ValueError):
    """A validation error that an API route can expose safely."""


def _as_uuid(value: object) -> UUID:
    try:
        return value if isinstance(value, UUID) else UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise AnalyticsError("Invalid analytics identity") from exc


def _scope_for_user(user: dict[str, object]) -> str:
    roles = {str(role).lower() for role in user.get("roles", [])}
    if {"administrator", "admin"} & roles:
        return "organization"
    if "approver" in roles or "report:approve" in set(user.get("permissions", [])):
        return "managed"
    return "personal"


def _month_key(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).strftime("%Y-%m")


def _money_rows(values: dict[tuple[str, ...], Decimal], *, include_category: bool = False) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, value in sorted(values.items()):
        if include_category:
            category, currency = key
            rows.append({"category": category, "currency": currency, "amount": float(value)})
        else:
            (currency,) = key
            rows.append({"currency": currency, "amount": float(value)})
    return rows


def overview(db: Session, user: dict[str, object], *, period_months: int = 6) -> dict[str, Any]:
    """Return a portable, tenant-safe aggregate dashboard for one actor.

    We aggregate in Python after bounded, indexed ORM queries. This deliberately
    avoids database-specific date bucket SQL so local SQLite tests and Neon
    PostgreSQL return identical result shapes. The period is bounded to keep
    dashboards predictable; detailed finance exports remain in the finance API.
    """

    if not 1 <= period_months <= 24:
        raise AnalyticsError("period_months must be between 1 and 24")

    actor_id = _as_uuid(user.get("user_id"))
    organization_id = _as_uuid(user.get("organization_id"))
    scope = _scope_for_user(user)
    now = datetime.now(UTC)
    period_start = now - timedelta(days=31 * period_months)

    query = (
        db.query(ExpenseReport)
        .join(User, User.id == ExpenseReport.employee_user_id)
        .filter(
            ExpenseReport.is_deleted.is_(False),
            User.is_deleted.is_(False),
            User.organization_id == organization_id,
            ExpenseReport.created_at >= period_start,
        )
    )
    if scope == "managed":
        assigned_report_ids = select(ApprovalLevel.expense_report_id).where(
            ApprovalLevel.approver_user_id == actor_id,
            ApprovalLevel.is_deleted.is_(False),
        )
        query = query.filter(
            or_(
                ExpenseReport.employee_user_id == actor_id,
                ExpenseReport.id.in_(assigned_report_ids),
            )
        )
    elif scope == "personal":
        query = query.filter(ExpenseReport.employee_user_id == actor_id)

    reports = query.order_by(ExpenseReport.created_at.asc(), ExpenseReport.id.asc()).all()
    report_ids = [report.id for report in reports]
    report_by_id = {report.id: report for report in reports}

    if report_ids:
        item_rows = (
            db.query(ExpenseItem, ExpenseCategory)
            .outerjoin(ExpenseCategory, ExpenseCategory.id == ExpenseItem.category_id)
            .filter(
                ExpenseItem.expense_report_id.in_(report_ids),
                ExpenseItem.is_deleted.is_(False),
            )
            .all()
        )
        history_rows = (
            db.query(ApprovalHistory)
            .filter(
                ApprovalHistory.expense_report_id.in_(report_ids),
                ApprovalHistory.is_deleted.is_(False),
            )
            .order_by(ApprovalHistory.performed_at.asc(), ApprovalHistory.created_at.asc())
            .all()
        )
    else:
        item_rows = []
        history_rows = []

    report_statuses = Counter(report.status for report in reports)
    total_requested: dict[tuple[str], Decimal] = defaultdict(lambda: Decimal("0"))
    monthly_spend: dict[tuple[str, str], Decimal] = defaultdict(lambda: Decimal("0"))
    for report in reports:
        currency = (report.currency_code or "INR").upper()
        amount = Decimal(report.total_amount or 0)
        total_requested[(currency,)] += amount
        if month := _month_key(report.created_at):
            monthly_spend[(month, currency)] += amount

    category_spend: dict[tuple[str, str], Decimal] = defaultdict(lambda: Decimal("0"))
    violation_count = 0
    for item, category in item_rows:
        report = report_by_id[item.expense_report_id]
        category_name = category.name if category and not category.is_deleted else "Uncategorized"
        currency = (item.currency_code or report.currency_code or "INR").upper()
        category_spend[(category_name, currency)] += Decimal(item.amount or 0)
        violation_count += int(bool(item.is_policy_violated))

    completed_at: dict[UUID, datetime] = {}
    for history in history_rows:
        if history.action == "approve" and history.performed_at:
            completed_at[history.expense_report_id] = history.performed_at
    approval_hours: list[float] = []
    for report in reports:
        if report.status not in {"approved_pending_payment", "paid"} or not report.submitted_at:
            continue
        finished_at = completed_at.get(report.id)
        if finished_at is None:
            continue
        submitted_at = report.submitted_at
        if submitted_at.tzinfo is None:
            submitted_at = submitted_at.replace(tzinfo=UTC)
        if finished_at.tzinfo is None:
            finished_at = finished_at.replace(tzinfo=UTC)
        elapsed = (finished_at - submitted_at).total_seconds() / 3600
        if elapsed >= 0:
            approval_hours.append(elapsed)

    item_count = len(item_rows)
    summary = {
        "report_count": len(reports),
        "pending_approval_count": report_statuses["submitted"],
        "approved_pending_payment_count": report_statuses["approved_pending_payment"],
        "paid_count": report_statuses["paid"],
        "rejected_count": report_statuses["rejected"],
        "policy_violation_count": violation_count,
        "policy_violation_item_rate": round(violation_count / item_count, 4) if item_count else 0.0,
        "average_approval_hours": round(sum(approval_hours) / len(approval_hours), 2) if approval_hours else None,
        "total_requested": _money_rows(total_requested),
    }
    return {
        "generated_at": now,
        "period_months": period_months,
        "scope": scope,
        "summary": summary,
        "report_statuses": [
            {"status": status, "count": count}
            for status, count in sorted(report_statuses.items())
        ],
        "spending_by_category": _money_rows(category_spend, include_category=True),
        "monthly_spend": [
            {"month": month, "currency": currency, "amount": float(amount)}
            for (month, currency), amount in sorted(monthly_spend.items())
        ],
    }
