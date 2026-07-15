from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin


class ExpenseReport(UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base):
    __tablename__ = "expense_reports"
    
    report_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    employee_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    department_id: Mapped[str] = mapped_column(ForeignKey("departments.id"), nullable=False)
    workflow_rule_id: Mapped[str | None] = mapped_column(ForeignKey("workflow_rules.id"), nullable=True)
    applied_policy_id: Mapped[str | None] = mapped_column(ForeignKey("policies.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    last_saved_at: Mapped[str] = mapped_column(String(50), nullable=True)
    submitted_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    __mapper_args__ = {"version_id_col": VersionMixin.version}
