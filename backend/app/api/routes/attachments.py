"""Receipt upload and authenticated attachment download routes."""

from __future__ import annotations

import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_permission
from app.models.expense_item import ExpenseItem
from app.models.expense_report import ExpenseReport
from app.models.policy import Policy
from app.services import report_service, storage_service
from app.services.upload_guard import UploadTooLargeError, read_bounded_upload_sync


router = APIRouter(tags=["attachments"])


def _uuid(value: str, field: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Invalid {field}") from exc


def _expense_item(db: Session, item_id: str) -> ExpenseItem:
    item = db.scalar(
        select(ExpenseItem).where(
            ExpenseItem.id == _uuid(item_id, "expense item id"),
            ExpenseItem.is_deleted.is_(False),
        )
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense item not found")
    return item


def _ensure_item_owner(db: Session, item: ExpenseItem, user: dict[str, str]) -> None:
    report = db.scalar(
        select(ExpenseReport).where(
            ExpenseReport.id == item.expense_report_id,
            ExpenseReport.is_deleted.is_(False),
        )
    )
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense report not found")
    if str(report.employee_user_id) != str(user["user_id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the report owner can upload its receipts")
    if report.status not in {"draft", "sent_back"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Receipts can only be changed on draft or sent-back reports")


@router.post("/api/items/{item_id}/receipt", status_code=status.HTTP_201_CREATED)
def upload_receipt(
    item_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: dict[str, str] = Depends(require_permission("report:create")),
):
    attachment = None
    stored_path: str | None = None
    committed = False
    try:
        item = _expense_item(db, item_id)
        _ensure_item_owner(db, item, user)
        content = read_bounded_upload_sync(
            file, max_bytes=storage_service._max_upload_bytes("receipt")
        )
        attachment = storage_service.create_attachment(
            db,
            entity_type="expense_item_receipt",
            entity_id=item.id,
            uploaded_by=user["user_id"],
            file_name=file.filename or "receipt",
            mime_type=file.content_type or "",
            content=content,
            kind="receipt",
        )
        stored_path = attachment.storage_path
        db.commit()
        committed = True
        db.refresh(attachment)
        return storage_service.attachment_payload(attachment)
    except UploadTooLargeError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)) from exc
    except storage_service.UploadValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except storage_service.StorageError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise
    finally:
        if stored_path is not None and not committed:
            try:
                storage_service.delete_storage_path(stored_path)
            except storage_service.StorageError:
                pass
        file.file.close()


@router.get("/api/attachments/{attachment_id}/download")
def download_attachment(
    attachment_id: str,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(get_current_user),
):
    attachment = storage_service.get_attachment(db, attachment_id)
    if attachment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    if attachment.entity_type == "expense_item_receipt":
        item = db.scalar(
            select(ExpenseItem).where(
                ExpenseItem.id == attachment.entity_id,
                ExpenseItem.is_deleted.is_(False),
            )
        )
        report = (
            db.scalar(
                select(ExpenseReport).where(
                    ExpenseReport.id == item.expense_report_id,
                    ExpenseReport.is_deleted.is_(False),
                )
            )
            if item is not None
            else None
        )
        if report is None or not report_service.can_read_report(db, report, user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this attachment")
    elif attachment.entity_type == "policy_document":
        permissions = set(user.get("permissions", []))
        is_global_operator = "*" in permissions
        if not is_global_operator and "policy:manage" not in permissions:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this attachment")
        policy_query = select(Policy).where(
            Policy.id == attachment.entity_id,
            Policy.uploaded_document_attachment_id == attachment.id,
            Policy.is_deleted.is_(False),
        )
        # Tenant administrators are never authorized merely because they hold
        # a broad policy permission.  Resolve the attachment's owner first and
        # apply the same tenant boundary used by policy administration.  ``*``
        # is reserved for an explicitly provisioned platform operator.
        if not is_global_operator:
            policy_query = policy_query.where(
                Policy.organization_id == uuid.UUID(str(user["organization_id"]))
            )
        if db.scalar(policy_query) is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this attachment")
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this attachment")
    try:
        content = storage_service.read_attachment(attachment)
    except storage_service.StorageError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    escaped_name = quote(attachment.original_file_name, safe="")
    return StreamingResponse(
        iter([content]),
        media_type=attachment.mime_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{escaped_name}"},
    )
