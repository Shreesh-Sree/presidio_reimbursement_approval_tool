"""Employee report editing, submission, line items, and discussion endpoints."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.report_schemas import CommentInput, LineItemCreateInput, LineItemUpdateInput, ReportCreateInput, ReportUpdateInput
from app.core.database import get_db
from app.core.deps import require_permission
from app.services import ai_review_client, approval_service, audit_service, comment_service, integration_outbox_service, item_service, notification_delivery_service, presentation_service, report_service


router = APIRouter(prefix="/api/reports", tags=["reports"])


def _raise_report_error(exc: Exception) -> None:
    if isinstance(exc, report_service.PolicyViolationError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": str(exc), "violations": exc.violations},
        ) from exc
    if isinstance(exc, (report_service.ReportError, item_service.ItemError, approval_service.ApprovalError, comment_service.CommentError)):
        detail = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if detail in {"Report not found", "Expense item not found"} else status.HTTP_422_UNPROCESSABLE_ENTITY
        raise HTTPException(status_code=status_code, detail=detail) from exc
    raise exc


def _report_for_access(db: Session, report_id: str, actor: dict[str, object]):
    report = report_service.get_report(db, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    if not report_service.can_read_report(db, report, actor):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this report")
    return report


@router.post("", status_code=status.HTTP_201_CREATED)
def create_report(
    payload: ReportCreateInput,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("report:create")),
):
    try:
        report = report_service.create_draft(
            db,
            user["user_id"],
            user["department_id"],
            payload.title,
            description=payload.description,
            start_date=payload.start_date,
            end_date=payload.end_date,
            currency_code=payload.currency,
        )
        return presentation_service.report_payload(db, report)
    except Exception as exc:
        _raise_report_error(exc)


@router.get("")
def list_user_reports(
    status_filter: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("report:read")),
):
    selected_status = status or status_filter
    reports = report_service.list_reports(db, employee_user_id=user["user_id"], status=selected_status)
    return [presentation_service.report_payload(db, report, include_items=False) for report in reports]


@router.get("/{report_id}")
def get_report(
    report_id: str,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("report:read")),
):
    report = _report_for_access(db, report_id, user)
    permissions = set(user.get("permissions", []))
    ai_audit = (
        ai_review_client.review_payload(report)
        if {"report:approve", "*"} & permissions
        else None
    )
    return presentation_service.report_payload(db, report, ai_audit=ai_audit)


@router.patch("/{report_id}")
def update_report(
    report_id: str,
    payload: ReportUpdateInput,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("report:create")),
):
    try:
        changes = payload.model_dump(exclude_unset=True)
        if "currency" in changes:
            changes["currency_code"] = changes.pop("currency")
        report = report_service.update_draft(db, report_id, user["user_id"], **changes)
        return presentation_service.report_payload(db, report)
    except Exception as exc:
        _raise_report_error(exc)


@router.post("/{report_id}/submit")
def submit_report(
    report_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("report:create")),
):
    try:
        report = report_service.get_report(db, report_id)
        if report is None:
            raise report_service.ReportError("Report not found")
        # Validate the hierarchy before committing the state transition.
        approval_service.validate_workflow_for_report(db, report)
        # Submission, task initialization, notifications, audit history, and
        # the minimized AI outbox intent must become visible together.  No
        # remote service is called from this request transaction.
        submitted = report_service.submit_report(db, report_id, user["user_id"], commit=False)
        approval_service.init_workflow(db, submitted, user["user_id"], commit=False)
        try:
            integration_outbox_service.enqueue_ai_review(db, submitted)
        except ai_review_client.AIReviewError:
            # AI advice is intentionally advisory. Preserve a core audit event
            # without provider/transport details, then leave human approval
            # live; the human workflow still commits atomically.
            audit_service.record_audit(
                db,
                "expense_reports",
                str(submitted.id),
                "ai_review_enqueue_unavailable",
                performed_by=str(user["user_id"]),
            )
        db.commit()
        db.refresh(submitted)
        notification_delivery_service.enqueue_pending_email_delivery(background_tasks)
        return presentation_service.report_payload(db, submitted)
    except report_service.PolicyViolationError as exc:
        # Validation flags are useful feedback on the editable draft.  This is
        # the one intentional non-submission commit; no report status changed.
        db.commit()
        _raise_report_error(exc)
    except Exception as exc:
        db.rollback()
        _raise_report_error(exc)


@router.post("/{report_id}/withdraw")
def withdraw_report(
    report_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("report:create")),
):
    try:
        report = report_service.withdraw_report(db, report_id, user["user_id"])
        notification_delivery_service.enqueue_pending_email_delivery(background_tasks)
        return presentation_service.report_payload(db, report)
    except Exception as exc:
        _raise_report_error(exc)


@router.post("/{report_id}/items", status_code=status.HTTP_201_CREATED)
def add_item(
    report_id: str,
    payload: LineItemCreateInput,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("report:create")),
):
    try:
        item = item_service.add_item(
            db,
            report_id,
            user_id=user["user_id"],
            **payload.model_dump(exclude={"currency"}),
            currency_code=payload.currency,
        )
        return presentation_service.item_payload(db, item)
    except Exception as exc:
        _raise_report_error(exc)


@router.get("/{report_id}/items")
def list_items(
    report_id: str,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("report:read")),
):
    _report_for_access(db, report_id, user)
    try:
        return [presentation_service.item_payload(db, item) for item in item_service.list_items(db, report_id)]
    except Exception as exc:
        _raise_report_error(exc)


@router.patch("/{report_id}/items/{item_id}")
def update_item(
    report_id: str,
    item_id: str,
    payload: LineItemUpdateInput,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("report:create")),
):
    try:
        item = item_service._require_item(db, item_id)
        if str(item.expense_report_id) != report_id:
            raise item_service.ItemError("Expense item does not belong to this report")
        changes = payload.model_dump(exclude_unset=True)
        if "currency" in changes:
            changes["currency_code"] = changes.pop("currency")
        updated = item_service.update_item(db, item_id, user_id=user["user_id"], **changes)
        return presentation_service.item_payload(db, updated)
    except Exception as exc:
        _raise_report_error(exc)


@router.delete("/{report_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    report_id: str,
    item_id: str,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("report:create")),
):
    try:
        item = item_service._require_item(db, item_id)
        if str(item.expense_report_id) != report_id:
            raise item_service.ItemError("Expense item does not belong to this report")
        item_service.delete_item(db, item_id, user_id=user["user_id"])
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        _raise_report_error(exc)


@router.get("/{report_id}/comments")
def list_comments(
    report_id: str,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("report:read")),
):
    try:
        comments = comment_service.list_comments(db, report_id, user)
        return [presentation_service.comment_payload(db, comment) for comment in comments]
    except Exception as exc:
        _raise_report_error(exc)


@router.post("/{report_id}/comments", status_code=status.HTTP_201_CREATED)
def add_comment(
    report_id: str,
    payload: CommentInput,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("report:read")),
):
    try:
        comment = comment_service.add_comment(
            db,
            report_id,
            user,
            payload.body,
            payload.visibility,
            payload.parent_comment_id,
        )
        return presentation_service.comment_payload(db, comment)
    except Exception as exc:
        _raise_report_error(exc)
