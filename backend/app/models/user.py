from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey

from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin


class User(UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base):
    __tablename__ = "users"
    
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    
    roles: Mapped[list] = relationship("Role", secondary="user_roles", viewonly=True)
