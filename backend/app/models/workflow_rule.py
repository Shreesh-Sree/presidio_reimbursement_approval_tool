"""Configurable report-routing rules for approval workflows."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Index, Integer, JSON, String, UniqueConstraint, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import SoftDeleteMixin, TimestampMixin, UUIDMixin, VersionMixin


class WorkflowRule(UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base):
    """Selects an ordered approval chain when its JSON conditions match a report."""

    __tablename__ = "workflow_rules"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_workflow_rules_organization_name"),
        # Retained for compatibility with the baseline schema and useful for
        # legacy/global administrative ordering queries.
        Index("ix_workflow_rules_priority_active", "priority", "is_active"),
        Index("ix_workflow_rules_organization_priority_active", "organization_id", "priority", "is_active"),
        Index("ix_workflow_rules_is_deleted", "is_deleted"),
    )

    # Routing ownership is a schema invariant, not a JSON convention.  That
    # prevents legacy/unscoped rows from participating in another tenant's
    # approval flow.
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    conditions_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    approval_chain_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __mapper_args__ = {"version_id_col": VersionMixin.version}
