"""Persistence for the individual decisions in a report approval workflow."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import SoftDeleteMixin, TimestampMixin, UUIDMixin, VersionMixin


class ApprovalLevel(UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base):
    """An approver assigned to one level of an expense report's workflow."""

    __tablename__ = "approval_levels"
    __table_args__ = (
        UniqueConstraint(
            "expense_report_id",
            "level_number",
            "approver_user_id",
            name="uq_approval_levels_report_level_approver",
        ),
        Index("ix_approval_levels_approver_status", "approver_user_id", "status"),
        Index("ix_approval_levels_status", "status"),
        Index("ix_approval_levels_is_deleted", "is_deleted"),
    )

    expense_report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("expense_reports.id"), nullable=False
    )
    approver_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    level_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    decision_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_parallel: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)

    __mapper_args__ = {"version_id_col": VersionMixin.version}
