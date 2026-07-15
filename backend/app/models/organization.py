from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String

from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin


class Organization(UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base):
    __tablename__ = "organizations"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
