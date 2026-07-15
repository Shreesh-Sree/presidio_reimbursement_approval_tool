"""Structured policy validation for draft expense reports.

The validator intentionally updates only per-item policy flags.  It never
changes a report's workflow state and never commits the caller's transaction,
so submission orchestration can safely block before moving a report forward.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.expense_category import ExpenseCategory
from app.models.expense_item import ExpenseItem
from app.models.expense_report import ExpenseReport
from app.models.policy import Policy, PolicyRule
from app.services import policy_service, storage_service
from app.services.report_service import organization_id_for_report


def _decimal(value: object | None) -> Decimal:
    return Decimal("0") if value is None else Decimal(str(value))


def _active_items(db: Session, report: ExpenseReport) -> list[ExpenseItem]:
    return list(
        db.scalars(
            select(ExpenseItem)
            .where(
                ExpenseItem.expense_report_id == report.id,
                ExpenseItem.is_deleted.is_(False),
            )
            .order_by(ExpenseItem.line_number.asc())
        )
    )


def _applicable(rule: PolicyRule, item: ExpenseItem) -> bool:
    """A null scope is a wildcard; defined scopes must match the line item."""

    return (
        (rule.category_id is None or rule.category_id == item.category_id)
        and (rule.vendor_id is None or rule.vendor_id == item.vendor_id)
    )


def _sum(items: list[ExpenseItem], predicate: Callable[[ExpenseItem], bool]) -> Decimal:
    return sum((_decimal(item.amount) for item in items if predicate(item)), Decimal("0"))


def _has_receipt(db: Session, item: ExpenseItem) -> bool:
    return storage_service.latest_entity_attachment(
        db,
        entity_type="expense_item_receipt",
        entity_id=item.id,
    ) is not None


def _policy_for_report(db: Session, report: ExpenseReport, policy: Policy | None) -> Policy | None:
    organization_id = organization_id_for_report(db, report)
    if policy is not None:
        if policy.organization_id != organization_id:
            raise policy_service.PolicyConflictError("Policy does not belong to the report organization")
        return policy
    if report.applied_policy_id:
        try:
            return policy_service.get_policy(db, report.applied_policy_id, organization_id)
        except policy_service.PolicyNotFoundError:
            return None
    return policy_service.get_active_policy(db, organization_id)


def validate_report(db: Session, report: ExpenseReport, policy: Policy | None = None) -> list[str]:
    """Recompute and persist per-item violation flags without committing.

    Parameters are deliberately stable for report submission code:
    ``validate_report(db, report, policy=None) -> list[str]``.  If no snapshot
    is attached to the report, the currently active policy is evaluated.  Each
    returned message is prefixed with the affected line number; matching item
    records receive the same reason in ``policy_violation_reason``.
    """

    selected_policy = _policy_for_report(db, report, policy)
    items = _active_items(db, report)
    if selected_policy is None:
        for item in items:
            item.is_policy_violated = False
            item.policy_violation_reason = None
        db.flush()
        return []

    rules = [rule for rule in selected_policy.rules if not rule.is_deleted]
    categories = {
        category.id: category
        for category in db.scalars(
            select(ExpenseCategory).where(
                ExpenseCategory.id.in_({item.category_id for item in items}),
                ExpenseCategory.is_deleted.is_(False),
            )
        )
    } if items else {}

    violations: list[str] = []
    for item in items:
        reasons: list[str] = []
        matching_rules = [rule for rule in rules if _applicable(rule, item)]
        receipt_available = _has_receipt(db, item)

        category = categories.get(item.category_id)
        if category and category.max_amount is not None and _decimal(item.amount) > _decimal(category.max_amount):
            reasons.append(f"Amount exceeds the {category.name} category limit")

        for rule in matching_rules:
            scoped_items = [candidate for candidate in items if _applicable(rule, candidate)]
            if rule.max_per_day is not None:
                daily_total = _sum(
                    scoped_items,
                    lambda candidate: candidate.expense_date == item.expense_date,
                )
                if daily_total > _decimal(rule.max_per_day):
                    reasons.append(f"Daily total {daily_total} exceeds policy limit {_decimal(rule.max_per_day)}")
            if rule.max_per_trip is not None:
                trip_total = _sum(scoped_items, lambda _candidate: True)
                if trip_total > _decimal(rule.max_per_trip):
                    reasons.append(f"Trip total {trip_total} exceeds policy limit {_decimal(rule.max_per_trip)}")
            if rule.per_category_cap is not None:
                category_total = _sum(
                    scoped_items,
                    lambda candidate: candidate.category_id == item.category_id,
                )
                if category_total > _decimal(rule.per_category_cap):
                    reasons.append(
                        f"Category total {category_total} exceeds policy cap {_decimal(rule.per_category_cap)}"
                    )
            if (
                rule.receipt_required_above is not None
                and _decimal(item.amount) >= _decimal(rule.receipt_required_above)
                and not receipt_available
            ):
                reasons.append(
                    f"A receipt is required for amounts at or above {_decimal(rule.receipt_required_above)}"
                )

        # A single generic receipt requirement can match more than one rule.
        # Preserve useful details while avoiding repeated identical messages.
        deduplicated_reasons = list(dict.fromkeys(reasons))
        item.is_policy_violated = bool(deduplicated_reasons)
        item.policy_violation_reason = "; ".join(deduplicated_reasons) or None
        if deduplicated_reasons:
            line_label = f"Line {item.line_number}" if item.line_number else f"Item {item.id}"
            violations.append(f"{line_label}: {item.policy_violation_reason}")

    # Flush marks the item flags visible to the current transaction but leaves
    # commit/rollback and report status entirely to the caller.
    db.flush()
    return violations
