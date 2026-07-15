from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String

from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin


class Permission(UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base):
    __tablename__ = "permissions"
    
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
