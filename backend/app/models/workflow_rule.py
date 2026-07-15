"""Configurable report-routing rules for approval workflows."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, Index, Integer, JSON, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import SoftDeleteMixin, TimestampMixin, UUIDMixin, VersionMixin


class WorkflowRule(UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base):
    """Selects an ordered approval chain when its JSON conditions match a report."""

    __tablename__ = "workflow_rules"
    __table_args__ = (
        Index("ix_workflow_rules_priority_active", "priority", "is_active"),
        Index("ix_workflow_rules_is_deleted", "is_deleted"),
    )

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    conditions_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    approval_chain_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __mapper_args__ = {"version_id_col": VersionMixin.version}
