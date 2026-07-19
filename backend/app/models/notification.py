"""In-app and delivery-channel notification persistence."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, synonym

from app.core.database import Base
from app.models.base import SoftDeleteMixin, TimestampMixin, UUIDMixin, VersionMixin


class Notification(UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base):
    """A notification that can be surfaced in-app and/or delivered externally."""

    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_recipient_created", "recipient_user_id", "created_at"),
        Index("ix_notifications_channel", "channel"),
        Index("ix_notifications_status", "status"),
        Index("ix_notifications_sent_at", "sent_at"),
        Index("ix_notifications_is_deleted", "is_deleted"),
        # Keep these aligned with the durable-delivery migration.  The first
        # supports ready-work scans; the second lets a replacement worker
        # reclaim rows after a crashed sender's lease expires.
        Index("ix_notifications_delivery_ready", "channel", "status", "next_attempt_at"),
        Index("ix_notifications_delivery_lease", "delivery_lease_expires_at"),
    )

    recipient_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    template_code: Mapped[str] = mapped_column(String(100), nullable=False)
    # "in_app" is the default feed channel; external senders may use email, push, or SMS.
    channel: Mapped[str] = mapped_column(String(20), default="in_app", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(
        "payload", JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivery_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # These fields implement a lease-based worker handoff.  A process crash
    # cannot leave a row indefinitely in ``sending`` because another worker
    # may reclaim it after the lease expires.
    delivery_attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivery_claim_token: Mapped[str | None] = mapped_column(String(100), nullable=True)
    delivery_claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivery_lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Retain the DBML's ``payload`` spelling for newer callers while keeping the
    # existing notification service's ``payload_json`` constructor argument.
    payload = synonym("payload_json")

    __mapper_args__ = {"version_id_col": VersionMixin.version}
