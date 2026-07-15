"""Immutable payment lifecycle events for finance and employee status history."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import SoftDeleteMixin, TimestampMixin, UUIDMixin, VersionMixin


class PaymentEvent(UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base):
    """A durable, non-sensitive transition record for a reimbursement payment."""

    __tablename__ = "payment_events"
    __table_args__ = (
        Index("ix_payment_events_payment_occurred", "payment_record_id", "occurred_at"),
        Index("ix_payment_events_batch", "payment_batch_id"),
        Index("ix_payment_events_performed", "performed_by", "occurred_at"),
        Index("ix_payment_events_is_deleted", "is_deleted"),
    )

    payment_record_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("payment_records.id"), nullable=False
    )
    payment_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("payment_batches.id"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    provider_reference: Mapped[str | None] = mapped_column(String(150), nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    performed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __mapper_args__ = {"version_id_col": VersionMixin.version}
