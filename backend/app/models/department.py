import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import SoftDeleteMixin, TimestampMixin, UUIDMixin, VersionMixin


class Department(UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base):
    __tablename__ = "departments"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_department_org_code"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    # Kept as an identifier rather than an FK so a department can be created
    # before its first employee.  It is validated by the administration service.
    department_head_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False, index=True)

    organization = relationship("Organization", back_populates="departments")
    members = relationship("User", back_populates="department", foreign_keys="User.department_id")
