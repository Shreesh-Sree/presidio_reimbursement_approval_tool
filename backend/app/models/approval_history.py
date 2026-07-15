"""Immutable-looking audit entries for report approval actions."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import SoftDeleteMixin, TimestampMixin, UUIDMixin, VersionMixin


class ApprovalHistory(UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base):
    """Records an approve, reject, send-back, or forwarding action on a report."""

    __tablename__ = "approval_history"
    __table_args__ = (
        Index("ix_approval_history_report_performed", "expense_report_id", "performed_at"),
        Index("ix_approval_history_approval_level", "approval_level_id"),
        Index("ix_approval_history_action", "action"),
        Index("ix_approval_history_performer_performed", "performed_by", "performed_at"),
        Index("ix_approval_history_acting_for_performed", "acting_for_user_id", "performed_at"),
        Index("ix_approval_history_is_deleted", "is_deleted"),
    )

    expense_report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("expense_reports.id"), nullable=False
    )
    approval_level_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("approval_levels.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    # System-generated workflow events (for example, SLA escalations) have no
    # human performer. Human approval decisions remain non-null in service
    # logic, while the nullable column preserves truthful automation history.
    performed_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    # Present only when a delegate (or an escalated approver) acts for the
    # workflow-selected approver. This makes the audit trail explicit without
    # changing the human decision itself.
    acting_for_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    performed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)

    __mapper_args__ = {"version_id_col": VersionMixin.version}
