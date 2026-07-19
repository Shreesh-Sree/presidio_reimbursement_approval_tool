"""Authenticated in-app notification feed."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.services import notification_service, presentation_service


router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("")
def list_notifications(
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(get_current_user),
):
    notifications = notification_service.unread_for_user(db, user["user_id"])
    return [presentation_service.notification_payload(notification) for notification in notifications]


@router.post("/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(get_current_user),
):
    try:
        notification = notification_service.mark_read(db, notification_id, user["user_id"])
        return presentation_service.notification_payload(notification)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found") from exc
