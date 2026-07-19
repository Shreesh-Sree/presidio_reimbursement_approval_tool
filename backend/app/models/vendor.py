import uuid

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin


class Vendor(UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base):
    __tablename__ = "vendors"
    __table_args__ = (
        UniqueConstraint("organization_id", "normalized_name", name="uq_vendors_organization_normalized_name"),
        Index("ix_vendors_organization_id", "organization_id"),
        Index("ix_vendors_is_deleted", "is_deleted"),
    )
    
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    __mapper_args__ = {"version_id_col": VersionMixin.version}
