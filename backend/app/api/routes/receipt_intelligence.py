"""Manual, report-authorized metadata checks via receipt intelligence."""

from __future__ import annotations

from decimal import Decimal
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.receipt_intelligence_schemas import (
    ReceiptAnalysisContextResponse,
    ReceiptAnalysisInput,
    ReceiptAnalysisResponse,
)
from app.core.database import get_db
from app.core.deps import require_permission
from app.models.expense_item import ExpenseItem
from app.models.expense_report import ExpenseReport
from app.models.policy import Policy, PolicyRule
from app.models.user import User
from app.services import policy_service, receipt_intelligence_client, report_service, storage_service


router = APIRouter(prefix="/api/reports", tags=["receipt-intelligence"])


def _uuid(value: str, *, label: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except (TypeError, ValueError, AttributeError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Invalid {label}") from exc


def _report_for_authorized_read(
    db: Session,
    report_id: str,
    user: dict[str, object],
) -> ExpenseReport:
    report = db.scalar(
        select(ExpenseReport).where(
            ExpenseReport.id == _uuid(report_id, label="report id"),
            ExpenseReport.is_deleted.is_(False),
        )
    )
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    employee = db.get(User, report.employee_user_id)
    if (
        employee is None
        or employee.is_deleted
        or str(employee.organization_id) != str(user.get("organization_id", ""))
        or not report_service.can_read_report(db, report, user)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this report")
    return report


def _item_for_report(db: Session, report: ExpenseReport, item_id: str) -> ExpenseItem:
    item = db.scalar(
        select(ExpenseItem).where(
            ExpenseItem.id == _uuid(item_id, label="expense item id"),
            ExpenseItem.is_deleted.is_(False),
        )
    )
    if item is None or item.expense_report_id != report.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense item not found")
    return item


def _receipt_for_item(
    db: Session,
    item: ExpenseItem,
    attachment_id: uuid.UUID | None,
):
    receipt = (
        storage_service.get_attachment(db, attachment_id)
        if attachment_id is not None
        else storage_service.latest_entity_attachment(
            db,
            entity_type="expense_item_receipt",
            entity_id=item.id,
        )
    )
    if receipt is not None and (receipt.entity_type != "expense_item_receipt" or receipt.entity_id != item.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt attachment not found")
    return receipt


def _policy_for_report(
    db: Session,
    report: ExpenseReport,
    organization_id: str | uuid.UUID,
) -> Policy | None:
    if report.applied_policy_id is not None:
        try:
            return policy_service.get_policy(db, report.applied_policy_id, organization_id)
        except policy_service.PolicyNotFoundError:
            return None
    return policy_service.get_active_policy(db, organization_id)


def _receipt_threshold(
    db: Session,
    report: ExpenseReport,
    item: ExpenseItem,
    organization_id: str | uuid.UUID,
) -> Decimal | None:
    """Return the strictest matching receipt threshold from the frozen policy."""

    policy = _policy_for_report(db, report, organization_id)
    if policy is None:
        return None
    thresholds = [
        Decimal(str(rule.receipt_required_above))
        for rule in policy.rules
        if not rule.is_deleted
        and rule.receipt_required_above is not None
        and (rule.category_id is None or rule.category_id == item.category_id)
        and (rule.vendor_id is None or rule.vendor_id == item.vendor_id)
    ]
    return min(thresholds) if thresholds else None


@router.post(
    "/{report_id}/items/{item_id}/receipt-analysis",
    response_model=ReceiptAnalysisResponse,
)
def analyze_receipt_metadata(
    report_id: str,
    item_id: str,
    payload: ReceiptAnalysisInput | None = None,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("report:read")),
):
    """Run an advisory check with explicit ephemeral OCR for supported receipt images."""

    report = _report_for_authorized_read(db, report_id, user)
    item = _item_for_report(db, report, item_id)
    receipt = _receipt_for_item(db, item, payload.attachment_id if payload else None)
    try:
        extracted_text = None
        if receipt is not None and receipt.mime_type in {"image/jpeg", "image/png", "image/webp"}:
            receipt_bytes = storage_service.read_attachment(receipt)
            extracted_text = receipt_intelligence_client.extract_receipt_text(
                content=receipt_bytes,
                media_type=receipt.mime_type,
            )
        result = receipt_intelligence_client.analyze_receipt(
            organization_id=str(user["organization_id"]),
            report_id=str(report.id),
            item_id=str(item.id),
            attachment_id=str(receipt.id) if receipt is not None else None,
            receipt_checksum=receipt.checksum if receipt is not None else None,
            receipt_mime_type=receipt.mime_type if receipt is not None else None,
            receipt_size_bytes=receipt.file_size_bytes if receipt is not None else None,
            expense_amount=Decimal(str(item.amount)),
            currency=item.currency_code or report.currency_code,
            receipt_required_at_or_above=_receipt_threshold(
                db,
                report,
                item,
                user["organization_id"],
            ),
            supplied_text=extracted_text,
            text_source="service_ocr" if extracted_text is not None else "not_provided",
        )
    except receipt_intelligence_client.ReceiptIntelligenceError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return ReceiptAnalysisResponse(
        advisory=True,
        context=ReceiptAnalysisContextResponse(
            organization_ref=result.context.organization_ref,
            report_ref=result.context.report_ref,
            item_ref=result.context.item_ref,
            attachment_ref=result.context.attachment_ref,
            event_id=result.context.event_id,
        ),
        analysis=result.analysis,
    )
