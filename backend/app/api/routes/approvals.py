"""Manager queue and human approval actions for submitted reports."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.report_schemas import ApprovalActionInput
from app.core.database import get_db
from app.core.deps import require_permission
from app.services import ai_review_client, approval_service, presentation_service


router = APIRouter(prefix="/api/approvals", tags=["approvals"])


def _raise_approval_error(exc: Exception) -> None:
    if isinstance(exc, approval_service.ApprovalError):
        detail = str(exc)
        code = status.HTTP_404_NOT_FOUND if detail == "Report not found" else status.HTTP_422_UNPROCESSABLE_ENTITY
        raise HTTPException(status_code=code, detail=detail) from exc
    raise exc


@router.get("/queue")
async def approval_queue(
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("report:approve")),
):
    entries = approval_service.queue_for_approver(db, user["user_id"])
    queue = []
    for level, report in entries:
        payload = presentation_service.report_payload(db, report, include_items=False)
        payload["pending_with"] = str(user["email"])
        payload["approval_level"] = level.level_number
        queue.append(payload)
    return queue


async def _take_action(
    report_id: str,
    action: str,
    payload: ApprovalActionInput,
    db: Session,
    user: dict[str, object],
):
    try:
        report = approval_service.act_on_report(db, report_id, user["user_id"], action, payload.remarks)
        ai_review_client.record_human_disposition(report, user["user_id"], action, payload.remarks)
        return presentation_service.report_payload(db, report)
    except Exception as exc:
        _raise_approval_error(exc)


@router.post("/{report_id}/approve")
async def approve(
    report_id: str,
    payload: ApprovalActionInput,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("report:approve")),
):
    return await _take_action(report_id, "approve", payload, db, user)


@router.post("/{report_id}/reject")
async def reject(
    report_id: str,
    payload: ApprovalActionInput,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("report:approve")),
):
    return await _take_action(report_id, "reject", payload, db, user)


@router.post("/{report_id}/send-back")
async def send_back(
    report_id: str,
    payload: ApprovalActionInput,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("report:approve")),
):
    return await _take_action(report_id, "send_back", payload, db, user)
