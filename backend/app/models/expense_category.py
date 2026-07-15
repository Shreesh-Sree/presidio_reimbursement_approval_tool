import uuid

from sqlalchemy import Boolean, ForeignKey, Index, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin


class ExpenseCategory(UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base):
    __tablename__ = "expense_categories"
    __table_args__ = (Index("ix_expense_categories_is_deleted", "is_deleted"),)
    
    parent_category_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("expense_categories.id"), nullable=True
    )
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    receipt_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_amount: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    
    parent = relationship("ExpenseCategory", remote_side=lambda: [ExpenseCategory.id])
    __mapper_args__ = {"version_id_col": VersionMixin.version}
