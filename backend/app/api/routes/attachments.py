"""Receipt upload and authenticated attachment download routes."""

from __future__ import annotations

import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_permission
from app.models.expense_item import ExpenseItem
from app.models.expense_report import ExpenseReport
from app.services import storage_service


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
async def upload_receipt(
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
        content = await file.read()
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
        await file.close()


@router.get("/api/attachments/{attachment_id}/download")
async def download_attachment(
    attachment_id: str,
    db: Session = Depends(get_db),
    _user: dict[str, str] = Depends(require_permission("report:read")),
):
    attachment = storage_service.get_attachment(db, attachment_id)
    if attachment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
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
