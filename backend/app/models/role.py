from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String

from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin


class Role(UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base):
    __tablename__ = "roles"
    
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    permissions: Mapped[list] = relationship("Permission", secondary="role_permissions", viewonly=True)
