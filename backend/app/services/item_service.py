"""Line-item editing with report ownership, totals, and live policy flags."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.expense_category import ExpenseCategory
from app.models.expense_item import ExpenseItem
from app.models.vendor import Vendor
from app.services.audit_service import record_audit
from app.services.report_service import (
    EDITABLE_STATUSES,
    ReportError,
    _as_uuid,
    _require_owner,
    _require_report,
    organization_id_for_report,
    recompute_total,
)


class ItemError(ReportError):
    """A user-correctable line-item error."""


def _require_item(db: Session, item_id: uuid.UUID | str) -> ExpenseItem:
    item = (
        db.query(ExpenseItem)
        .filter(ExpenseItem.id == _as_uuid(item_id), ExpenseItem.is_deleted.is_(False))
        .first()
    )
    if not item:
        raise ItemError("Expense item not found")
    return item


def _resolve_category(
    db: Session,
    category_id: uuid.UUID | str | None,
    category_name: str | None,
    organization_id: uuid.UUID,
) -> ExpenseCategory:
    category = None
    if category_id:
        try:
            category = (
                db.query(ExpenseCategory)
                .filter(
                    ExpenseCategory.id == _as_uuid(category_id),
                    ExpenseCategory.organization_id == organization_id,
                    ExpenseCategory.is_deleted.is_(False),
                )
                .first()
            )
        except ValueError:
            category = None
    if category is None and category_name:
        normalized = category_name.strip()
        category = (
            db.query(ExpenseCategory)
            .filter(
                ExpenseCategory.is_deleted.is_(False),
                ExpenseCategory.organization_id == organization_id,
                or_(ExpenseCategory.name.ilike(normalized), ExpenseCategory.code.ilike(normalized)),
            )
            .first()
        )
    if not category:
        raise ItemError("Select a valid expense category")
    return category


def _resolve_vendor(
    db: Session,
    vendor_id: uuid.UUID | str | None,
    vendor_name: str | None,
    organization_id: uuid.UUID,
) -> Vendor | None:
    vendor = None
    if vendor_id:
        try:
            vendor = (
                db.query(Vendor)
                .filter(
                    Vendor.id == _as_uuid(vendor_id),
                    Vendor.organization_id == organization_id,
                    Vendor.is_deleted.is_(False),
                )
                .first()
            )
        except ValueError:
            vendor = None
    if vendor is None and vendor_name and vendor_name.strip():
        normalized = vendor_name.strip().lower().replace(" ", "_")
        vendor = (
            db.query(Vendor)
            .filter(
                Vendor.is_deleted.is_(False),
                Vendor.organization_id == organization_id,
                or_(Vendor.normalized_name == normalized, Vendor.name.ilike(vendor_name.strip())),
            )
            .first()
        )
    if vendor_id and vendor is None:
        raise ItemError("Select a valid vendor")
    return vendor


def _ensure_editable_owner(db: Session, item: ExpenseItem, user_id: uuid.UUID | str):
    report = _require_report(db, item.expense_report_id)
    _require_owner(report, user_id)
    if report.status not in EDITABLE_STATUSES:
        raise ItemError("Only draft or sent-back reports can be edited")
    return report


def _refresh_policy_flags(db: Session, report) -> None:
    """Evaluate the current policy while a report is being drafted.

    Submission snapshots the policy separately.  These draft flags are advisory
    until submit, but make violations visible as soon as an employee edits an
    item.
    """

    from app.services.policy_service import get_active_policy
    from app.services.validation_service import validate_report

    policy = get_active_policy(db, organization_id_for_report(db, report))
    if policy:
        validate_report(db, report, policy=policy)
    else:
        for item in get_items(db, report.id):
            item.is_policy_violated = False
            item.policy_violation_reason = None


def _next_line_number(db: Session, report_id: uuid.UUID) -> int:
    return int(
        db.query(func.coalesce(func.max(ExpenseItem.line_number), 0))
        .filter(ExpenseItem.expense_report_id == report_id)
        .scalar()
        or 0
    ) + 1


def add_item(
    db: Session,
    report_id: uuid.UUID | str,
    *,
    user_id: uuid.UUID | str,
    category_id: uuid.UUID | str | None = None,
    category_name: str | None = None,
    vendor_id: uuid.UUID | str | None = None,
    vendor_name: str | None = None,
    merchant_name: str | None = None,
    amount: Decimal | float | int,
    description: str | None = None,
    expense_date: date,
    currency_code: str | None = None,
) -> ExpenseItem:
    report = _require_report(db, report_id)
    _require_owner(report, user_id)
    if report.status not in EDITABLE_STATUSES:
        raise ItemError("Only draft or sent-back reports can be edited")
    amount_decimal = Decimal(str(amount))
    if amount_decimal <= 0:
        raise ItemError("Expense amount must be greater than zero")
    organization_id = organization_id_for_report(db, report)
    category = _resolve_category(db, category_id, category_name, organization_id)
    vendor = _resolve_vendor(db, vendor_id, vendor_name, organization_id)
    item = ExpenseItem(
        expense_report_id=report.id,
        line_number=_next_line_number(db, report.id),
        category_id=category.id,
        vendor_id=vendor.id if vendor else None,
        merchant_name=(merchant_name or (vendor.name if vendor else vendor_name) or None),
        amount=amount_decimal,
        original_amount=amount_decimal,
        currency_code=(currency_code or report.currency_code).upper(),
        expense_date=expense_date,
        description=description.strip() if description else None,
    )
    db.add(item)
    db.flush()
    recompute_total(db, report)
    _refresh_policy_flags(db, report)
    record_audit(
        db,
        "expense_items",
        str(item.id),
        "create",
        after={"amount": str(item.amount), "report_id": str(report.id), "category_id": str(category.id)},
        performed_by=str(user_id),
    )
    db.commit()
    db.refresh(item)
    return item


def update_item(
    db: Session,
    item_id: uuid.UUID | str,
    *,
    user_id: uuid.UUID | str,
    **changes: Any,
) -> ExpenseItem:
    item = _require_item(db, item_id)
    report = _ensure_editable_owner(db, item, user_id)
    before = {
        "amount": str(item.amount),
        "description": item.description,
        "category_id": str(item.category_id),
        "vendor_id": str(item.vendor_id) if item.vendor_id else None,
    }

    if "amount" in changes and changes["amount"] is not None:
        amount = Decimal(str(changes["amount"]))
        if amount <= 0:
            raise ItemError("Expense amount must be greater than zero")
        item.amount = amount
    if "category_id" in changes or "category_name" in changes:
        category = _resolve_category(
            db,
            changes.get("category_id"),
            changes.get("category_name"),
            organization_id_for_report(db, report),
        )
        item.category_id = category.id
    if "vendor_id" in changes or "vendor_name" in changes:
        vendor = _resolve_vendor(
            db,
            changes.get("vendor_id"),
            changes.get("vendor_name"),
            organization_id_for_report(db, report),
        )
        item.vendor_id = vendor.id if vendor else None
        if not changes.get("merchant_name") and vendor:
            item.merchant_name = vendor.name
    allowed = {"merchant_name", "description", "expense_date", "currency_code", "original_amount", "exchange_rate", "remarks"}
    for field in allowed:
        if field in changes and changes[field] is not None:
            value = changes[field]
            if field == "currency_code":
                value = str(value).upper()
            if field in {"merchant_name", "description", "remarks"} and isinstance(value, str):
                value = value.strip() or None
            setattr(item, field, value)

    recompute_total(db, report)
    _refresh_policy_flags(db, report)
    record_audit(
        db,
        "expense_items",
        str(item.id),
        "update",
        before=before,
        after={"amount": str(item.amount), "description": item.description, "category_id": str(item.category_id)},
        performed_by=str(user_id),
    )
    db.commit()
    db.refresh(item)
    return item


def delete_item(db: Session, item_id: uuid.UUID | str, *, user_id: uuid.UUID | str) -> None:
    item = _require_item(db, item_id)
    report = _ensure_editable_owner(db, item, user_id)
    item.is_deleted = True
    item.deleted_at = datetime.now(UTC)
    recompute_total(db, report)
    _refresh_policy_flags(db, report)
    record_audit(
        db,
        "expense_items",
        str(item.id),
        "delete",
        before={"amount": str(item.amount), "report_id": str(report.id)},
        performed_by=str(user_id),
    )
    db.commit()


def list_items(db: Session, report_id: uuid.UUID | str) -> list[ExpenseItem]:
    report = _require_report(db, report_id)
    return get_items(db, report.id)


def get_items(db: Session, report_id: uuid.UUID | str) -> list[ExpenseItem]:
    return (
        db.query(ExpenseItem)
        .filter(ExpenseItem.expense_report_id == _as_uuid(report_id), ExpenseItem.is_deleted.is_(False))
        .order_by(ExpenseItem.line_number)
        .all()
    )
