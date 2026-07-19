"""Persistent in-app notifications with optional future delivery channels."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.models.notification import Notification


def notify(
    db: Session,
    recipient_id: uuid.UUID | str,
    template_code: str,
    payload: dict[str, Any],
    channels: Iterable[str] = ("in_app",),
) -> list[Notification]:
    """Stage one notification per requested channel in the current transaction.

    In-app notifications are immediately available.  Other channels remain
    ``pending`` for a delivery worker, avoiding outbound network calls in a
    request transaction and keeping retries/auditability separate.
    """

    recipient_uuid = recipient_id if isinstance(recipient_id, uuid.UUID) else uuid.UUID(str(recipient_id))
    notifications: list[Notification] = []
    for channel in dict.fromkeys(channels):
        if channel not in {"in_app", "email"}:
            raise ValueError(f"Unsupported notification channel: {channel}")
        notification = Notification(
            recipient_user_id=recipient_uuid,
            template_code=template_code,
            channel=channel,
            status="sent" if channel == "in_app" else "pending",
            payload_json=payload,
            sent_at=datetime.now(UTC) if channel == "in_app" else None,
            next_attempt_at=datetime.now(UTC) if channel == "email" else None,
        )
        db.add(notification)
        notifications.append(notification)
    return notifications


def unread_for_user(db: Session, user_id: uuid.UUID | str) -> list[Notification]:
    recipient_uuid = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))
    return (
        db.query(Notification)
        .filter(
            Notification.recipient_user_id == recipient_uuid,
            Notification.channel == "in_app",
            Notification.is_deleted.is_(False),
        )
        .order_by(Notification.created_at.desc())
        .all()
    )


def mark_read(db: Session, notification_id: uuid.UUID | str, user_id: uuid.UUID | str) -> Notification:
    notification_uuid = notification_id if isinstance(notification_id, uuid.UUID) else uuid.UUID(str(notification_id))
    recipient_uuid = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))
    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_uuid,
            Notification.recipient_user_id == recipient_uuid,
            Notification.is_deleted.is_(False),
        )
        .first()
    )
    if not notification:
        raise ValueError("Notification not found")
    if notification.read_at is None:
        notification.read_at = datetime.now(UTC)
        db.commit()
        db.refresh(notification)
    return notification
