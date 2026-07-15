"""Finance-owned batch metadata for reimbursement payment exports."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import SoftDeleteMixin, TimestampMixin, UUIDMixin, VersionMixin


class PaymentBatch(UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base):
    """A non-sensitive, auditable collection of payment records for export."""

    __tablename__ = "payment_batches"
    __table_args__ = (
        UniqueConstraint("organization_id", "batch_reference", name="uq_payment_batches_org_reference"),
        Index("ix_payment_batches_organization_status", "organization_id", "status"),
        Index("ix_payment_batches_created_by", "created_by"),
        Index("ix_payment_batches_is_deleted", "is_deleted"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    batch_reference: Mapped[str] = mapped_column(String(150), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="created", nullable=False)
    currency_code: Mapped[str] = mapped_column(String(10), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    payment_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)

    __mapper_args__ = {"version_id_col": VersionMixin.version}
