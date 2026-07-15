"""Manager queue and human approval actions for submitted reports."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.report_schemas import ApprovalActionInput
from app.core.database import get_db
from app.core.deps import require_permission
from app.models.user import User
from app.services import ai_review_client, approval_service, notification_delivery_service, presentation_service


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
    # This idempotent sweep keeps local/small deployments responsive without
    # assigning an outcome automatically. Production can invoke the same
    # service from a scheduler for stricter SLA timing.
    approval_service.process_overdue_approvals(db, organization_id=user["organization_id"])
    entries = approval_service.queue_for_approver(db, user["user_id"])
    queue = []
    for level, report in entries:
        payload = presentation_service.report_payload(db, report, include_items=False)
        payload["pending_with"] = str(user["email"])
        payload["approval_level"] = level.level_number
        original_approver_id = level.original_approver_user_id or level.approver_user_id
        if original_approver_id != level.approver_user_id:
            original_approver = db.get(User, original_approver_id)
            payload["acting_for_name"] = original_approver.full_name if original_approver else None
        queue.append(payload)
    return queue


@router.get("/history")
async def approval_history(
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("report:approve")),
):
    entries = approval_service.history_for_approver(db, user["user_id"])
    history = []
    for level, report in entries:
        payload = presentation_service.report_payload(db, report, include_items=False)
        payload["approval_status"] = level.status
        payload["approval_decision_at"] = level.decision_date.isoformat() if level.decision_date else None
        history.append(payload)
    return history


async def _take_action(
    report_id: str,
    action: str,
    payload: ApprovalActionInput,
    background_tasks: BackgroundTasks,
    db: Session,
    user: dict[str, object],
):
    try:
        report = approval_service.act_on_report(db, report_id, user["user_id"], action, payload.remarks)
        ai_review_client.record_human_disposition(report, user["user_id"], action, payload.remarks)
        notification_delivery_service.enqueue_pending_email_delivery(background_tasks)
        return presentation_service.report_payload(db, report)
    except Exception as exc:
        _raise_approval_error(exc)


@router.post("/{report_id}/approve")
async def approve(
    report_id: str,
    payload: ApprovalActionInput,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("report:approve")),
):
    return await _take_action(report_id, "approve", payload, background_tasks, db, user)


@router.post("/{report_id}/reject")
async def reject(
    report_id: str,
    payload: ApprovalActionInput,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("report:approve")),
):
    return await _take_action(report_id, "reject", payload, background_tasks, db, user)


@router.post("/{report_id}/send-back")
async def send_back(
    report_id: str,
    payload: ApprovalActionInput,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("report:approve")),
):
    return await _take_action(report_id, "send_back", payload, background_tasks, db, user)
