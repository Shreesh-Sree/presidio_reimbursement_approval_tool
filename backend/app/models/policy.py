from datetime import datetime
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin


class Policy(UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base):
    __tablename__ = "policies"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version_label: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    uploaded_document_attachment_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    
    rules = relationship("PolicyRule", back_populates="policy", cascade="all, delete-orphan")
    __mapper_args__ = {"version_id_col": VersionMixin.version}


class PolicyRule(UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base):
    __tablename__ = "policy_rules"
    
    policy_id: Mapped[str] = mapped_column(ForeignKey("policies.id"), nullable=False)
    category_id: Mapped[str | None] = mapped_column(ForeignKey("expense_categories.id"), nullable=True)
    vendor_id: Mapped[str | None] = mapped_column(ForeignKey("vendors.id"), nullable=True)
    max_per_day: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    max_per_trip: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    per_category_cap: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    receipt_required_above: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    
    policy = relationship("Policy", back_populates="rules")
    __mapper_args__ = {"version_id_col": VersionMixin.version}
