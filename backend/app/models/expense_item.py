from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin


class ExpenseItem(UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base):
    __tablename__ = "expense_items"
    
    expense_report_id: Mapped[str] = mapped_column(ForeignKey("expense_reports.id"), nullable=False)
    line_number: Mapped[int] = mapped_column(nullable=False)
    category_id: Mapped[str] = mapped_column(ForeignKey("expense_categories.id"), nullable=False)
    vendor_id: Mapped[str | None] = mapped_column(ForeignKey("vendors.id"), nullable=True)
    merchant_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    original_amount: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    exchange_rate: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    expense_date: Mapped[str] = mapped_column(Date, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_policy_violated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    policy_violation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    __mapper_args__ = {"version_id_col": VersionMixin.version}
