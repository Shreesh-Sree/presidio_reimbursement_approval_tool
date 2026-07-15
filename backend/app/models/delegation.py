"""Temporary delegation of an employee's workflow responsibilities."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import SoftDeleteMixin, TimestampMixin, UUIDMixin, VersionMixin


class Delegation(UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base):
    """Allows a user to delegate all, expense, or approval work for a date range."""

    __tablename__ = "delegations"
    __table_args__ = (
        Index(
            "ix_delegations_delegator_delegate_dates",
            "delegator_user_id",
            "delegate_user_id",
            "start_date",
            "end_date",
        ),
        Index("ix_delegations_delegate", "delegate_user_id"),
        Index("ix_delegations_scope", "scope"),
        Index("ix_delegations_is_active", "is_active"),
        Index("ix_delegations_is_deleted", "is_deleted"),
    )

    delegator_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    delegate_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scope: Mapped[str] = mapped_column(String(20), default="all", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)

    __mapper_args__ = {"version_id_col": VersionMixin.version}
