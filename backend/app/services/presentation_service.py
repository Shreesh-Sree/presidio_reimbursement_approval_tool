"""Stable JSON payloads shared by report, approval, and collaboration routes."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.approval_history import ApprovalHistory
from app.models.comment import Comment
from app.models.expense_category import ExpenseCategory
from app.models.expense_item import ExpenseItem
from app.models.expense_report import ExpenseReport
from app.models.user import User
from app.models.vendor import Vendor
from app.services import approval_service, item_service, payment_service, storage_service


def _iso(value) -> str | None:
    return value.isoformat() if value is not None else None


def item_payload(db: Session, item: ExpenseItem) -> dict[str, Any]:
    category = db.get(ExpenseCategory, item.category_id) if item.category_id else None
    vendor = db.get(Vendor, item.vendor_id) if item.vendor_id else None
    receipt = storage_service.latest_entity_attachment(
        db,
        entity_type="expense_item_receipt",
        entity_id=item.id,
    )
    receipt_data = storage_service.attachment_payload(receipt) if receipt else None
    return {
        "id": str(item.id),
        "line_number": item.line_number,
        "category_id": str(item.category_id) if item.category_id else None,
        "category_name": category.name if category else None,
        "vendor_id": str(item.vendor_id) if item.vendor_id else None,
        "vendor_name": vendor.name if vendor else item.merchant_name,
        "merchant_name": item.merchant_name,
        "amount": float(item.amount),
        "original_amount": float(item.original_amount) if item.original_amount is not None else None,
        "currency": item.currency_code,
        "currency_code": item.currency_code,
        "expense_date": _iso(item.expense_date),
        "description": item.description or "",
        "receipt": receipt_data,
        "receipt_url": receipt_data["url"] if receipt_data else None,
        "is_policy_violated": item.is_policy_violated,
        "violation_reason": item.policy_violation_reason,
        "policy_violation_reason": item.policy_violation_reason,
    }


def approval_history_payload(db: Session, history: ApprovalHistory) -> dict[str, Any]:
    actor = db.get(User, history.performed_by) if history.performed_by else None
    acting_for = db.get(User, history.acting_for_user_id) if history.acting_for_user_id else None
    return {
        "id": str(history.id),
        "action": history.action,
        "actor_id": str(history.performed_by) if history.performed_by else None,
        "actor_name": actor.full_name if actor else "Workflow automation",
        "acting_for_user_id": str(history.acting_for_user_id) if history.acting_for_user_id else None,
        "acting_for_name": acting_for.full_name if acting_for else None,
        "remarks": history.remarks,
        "created_at": _iso(history.performed_at or history.created_at),
    }


def report_payload(
    db: Session,
    report: ExpenseReport,
    *,
    include_items: bool = True,
    ai_audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    employee = db.get(User, report.employee_user_id)
    items = [item_payload(db, item) for item in item_service.get_items(db, report.id)] if include_items else []
    history = [
        approval_history_payload(db, entry)
        for entry in approval_service.approval_history_for_report(db, report.id)
    ]
    violations = [
        item["violation_reason"]
        for item in items
        if item["is_policy_violated"] and item["violation_reason"]
    ]
    return {
        "id": str(report.id),
        "report_number": report.report_number,
        "title": report.title,
        "description": report.description,
        "start_date": _iso(report.start_date),
        "end_date": _iso(report.end_date),
        "status": report.status,
        "total": float(report.total_amount),
        "currency": report.currency_code,
        "created_at": _iso(report.created_at),
        "updated_at": _iso(report.updated_at),
        "submitted_at": _iso(report.submitted_at),
        "submitter_name": employee.full_name if employee else None,
        "submitter_email": employee.email if employee else None,
        "line_items": items,
        "items": items,
        "approval_history": history,
        "payment": payment_service.payment_for_report_payload(db, report),
        "ai_audit": ai_audit,
        "violations": violations,
    }


def comment_payload(db: Session, comment: Comment) -> dict[str, Any]:
    author = db.get(User, comment.author_user_id)
    return {
        "id": str(comment.id),
        "body": comment.text,
        "visibility": comment.visibility,
        "author_id": str(comment.author_user_id),
        "author_name": author.full_name if author else None,
        "parent_comment_id": str(comment.parent_comment_id) if comment.parent_comment_id else None,
        "created_at": _iso(comment.created_at),
    }


def notification_payload(notification) -> dict[str, Any]:
    payload = notification.payload_json or {}
    return {
        "id": str(notification.id),
        "title": payload.get("title") or notification.template_code.replace("_", " ").title(),
        "body": payload.get("body"),
        "type": payload.get("type") or notification.template_code,
        "report_id": payload.get("report_id"),
        "created_at": _iso(notification.created_at),
        "read_at": _iso(notification.read_at),
    }
