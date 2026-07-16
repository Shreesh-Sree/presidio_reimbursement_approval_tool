import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin


class ExpenseReport(UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base):
    __tablename__ = "expense_reports"
    __table_args__ = (
        Index("ix_expense_reports_employee_status", "employee_user_id", "status"),
        Index("ix_expense_reports_department_status", "department_id", "status"),
        Index("ix_expense_reports_is_deleted", "is_deleted"),
    )
    
    report_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    employee_user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    department_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("departments.id"), nullable=False)
    workflow_rule_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("workflow_rules.id"), nullable=True)
    applied_policy_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("policies.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    currency_code: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    last_saved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # This is only an opaque pointer to the AI service's own datastore.  Core
    # reimbursement data never stores AI prompts, findings, or provider output.
    ai_review_job_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    ai_review_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    __mapper_args__ = {"version_id_col": VersionMixin.version}
