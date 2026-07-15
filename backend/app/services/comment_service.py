"""Report discussions with employee-safe visibility rules."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.comment import Comment
from app.services.audit_service import record_audit
from app.services.report_service import ReportError, _as_uuid, _require_report, can_read_report


class CommentError(ReportError):
    pass


VISIBILITIES = {"all", "employee", "internal"}


def _is_report_owner(report, actor: dict[str, Any]) -> bool:
    return report.employee_user_id == _as_uuid(actor["user_id"])


def _is_approver_or_admin(actor: dict[str, Any]) -> bool:
    roles = {str(role).lower() for role in actor.get("roles", [])}
    permissions = set(actor.get("permissions", []))
    return "administrator" in roles or "admin" in roles or "report:approve" in permissions or "*" in permissions


def list_comments(db: Session, report_id: uuid.UUID | str, actor: dict[str, Any]) -> list[Comment]:
    report = _require_report(db, report_id)
    if not can_read_report(db, report, actor):
        raise CommentError("You do not have access to this report")
    query = db.query(Comment).filter(Comment.expense_report_id == report.id, Comment.is_deleted.is_(False))
    if not _is_approver_or_admin(actor):
        query = query.filter(Comment.visibility.in_(("all", "employee")))
    return query.order_by(Comment.created_at.asc()).all()


def add_comment(
    db: Session,
    report_id: uuid.UUID | str,
    actor: dict[str, Any],
    text: str,
    visibility: str = "employee",
    parent_comment_id: uuid.UUID | str | None = None,
) -> Comment:
    report = _require_report(db, report_id)
    if not can_read_report(db, report, actor):
        raise CommentError("You do not have access to this report")
    cleaned_text = text.strip()
    if not cleaned_text:
        raise CommentError("Comment text is required")
    if visibility not in VISIBILITIES:
        raise CommentError("Invalid comment visibility")
    if visibility == "internal" and not _is_approver_or_admin(actor):
        raise CommentError("Only approvers can create internal comments")
    if parent_comment_id is not None:
        try:
            parent_id = _as_uuid(parent_comment_id)
        except ValueError as exc:
            raise CommentError("Invalid parent comment") from exc
        parent = db.query(Comment).filter(Comment.id == parent_id, Comment.expense_report_id == report.id).first()
        if not parent:
            raise CommentError("Parent comment does not belong to this report")
    else:
        parent_id = None
    comment = Comment(
        expense_report_id=report.id,
        parent_comment_id=parent_id,
        author_user_id=_as_uuid(actor["user_id"]),
        text=cleaned_text,
        visibility=visibility,
    )
    db.add(comment)
    db.flush()
    record_audit(
        db,
        "comments",
        str(comment.id),
        "create",
        after={"report_id": str(report.id), "visibility": visibility},
        performed_by=str(actor["user_id"]),
    )
    db.commit()
    db.refresh(comment)
    return comment
