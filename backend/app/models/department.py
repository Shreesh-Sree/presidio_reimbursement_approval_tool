from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin


class Department(UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base):
    __tablename__ = "departments"
    
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    department_head_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    __mapper_args__ = {"version_id_col": VersionMixin.version}
