"""Transactional outbox rows for bounded, retryable integration handoffs."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Integer, JSON, String, Text, Uuid, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import SoftDeleteMixin, TimestampMixin, UUIDMixin, VersionMixin


class IntegrationOutbox(UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base):
    """A database-backed integration intent; payloads must already be minimized."""

    __tablename__ = "integration_outbox"
    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_integration_outbox_dedupe_key"),
        Index("ix_integration_outbox_ready", "status", "available_at"),
        Index("ix_integration_outbox_lease", "locked_until"),
    )

    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(255), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(
        "payload", JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    locked_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __mapper_args__ = {"version_id_col": VersionMixin.version}
