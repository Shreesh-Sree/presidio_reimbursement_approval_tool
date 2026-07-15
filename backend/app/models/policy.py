from datetime import datetime
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin


class Policy(UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base):
    __tablename__ = "policies"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", "version_label", name="uq_policies_organization_name_version"),
        Index("ix_policies_organization_active", "organization_id", "is_active"),
        Index("ix_policies_is_active", "is_active"),
        Index("ix_policies_is_deleted", "is_deleted"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version_label: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    uploaded_document_attachment_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    
    organization = relationship("Organization", back_populates="policies")
    rules = relationship("PolicyRule", back_populates="policy", cascade="all, delete-orphan")
    __mapper_args__ = {"version_id_col": VersionMixin.version}


class PolicyRule(UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base):
    __tablename__ = "policy_rules"
    __table_args__ = (
        UniqueConstraint("policy_id", "category_id", "vendor_id", name="uq_policy_rules_scope"),
        Index("ix_policy_rules_is_deleted", "is_deleted"),
    )
    
    policy_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("policies.id"), nullable=False)
    category_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("expense_categories.id"), nullable=True)
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("vendors.id"), nullable=True)
    max_per_day: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    max_per_trip: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    per_category_cap: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    receipt_required_above: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    
    policy = relationship("Policy", back_populates="rules")
    __mapper_args__ = {"version_id_col": VersionMixin.version}
