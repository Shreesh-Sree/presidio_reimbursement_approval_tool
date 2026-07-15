"""Payment-processing records for fully approved expense reports."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import SoftDeleteMixin, TimestampMixin, UUIDMixin, VersionMixin


class PaymentRecord(UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base):
    """Tracks a reimbursement's finance-system payment lifecycle."""

    __tablename__ = "payment_records"
    __table_args__ = (
        Index("ix_payment_records_expense_report", "expense_report_id"),
        Index("ix_payment_records_bank_detail", "bank_detail_id"),
        Index("ix_payment_records_status_date", "status", "payment_date"),
        Index("ix_payment_records_processed_by", "processed_by"),
        Index("ix_payment_records_is_deleted", "is_deleted"),
    )

    expense_report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("expense_reports.id"), nullable=False
    )
    # The original DBML references a future bank_details table. Keep this UUID
    # nullable and unbound until that bounded context is introduced, so the
    # current metadata remains migratable as a complete schema.
    bank_detail_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    payment_reference: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    processed_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)

    __mapper_args__ = {"version_id_col": VersionMixin.version}
