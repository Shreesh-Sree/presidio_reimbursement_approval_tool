from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, ForeignKey

from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin


class UserRole(UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base):
    __tablename__ = "user_roles"
    
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    role_id: Mapped[str] = mapped_column(String(36), ForeignKey("roles.id"), nullable=False)
