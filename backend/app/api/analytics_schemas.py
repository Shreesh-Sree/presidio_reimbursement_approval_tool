"""Read-only contracts for privacy-conscious reimbursement analytics."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.api.schemas import ApiModel


class CurrencyAmount(ApiModel):
    currency: str = Field(min_length=3, max_length=10)
    amount: float = Field(ge=0)


class CategorySpend(ApiModel):
    category: str = Field(min_length=1, max_length=255)
    currency: str = Field(min_length=3, max_length=10)
    amount: float = Field(ge=0)


class StatusCount(ApiModel):
    status: str = Field(min_length=1, max_length=50)
    count: int = Field(ge=0)


class MonthlySpend(ApiModel):
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    currency: str = Field(min_length=3, max_length=10)
    amount: float = Field(ge=0)


class AnalyticsSummary(ApiModel):
    report_count: int = Field(ge=0)
    pending_approval_count: int = Field(ge=0)
    approved_pending_payment_count: int = Field(ge=0)
    paid_count: int = Field(ge=0)
    rejected_count: int = Field(ge=0)
    policy_violation_count: int = Field(ge=0)
    policy_violation_item_rate: float = Field(ge=0, le=1)
    average_approval_hours: float | None = Field(default=None, ge=0)
    total_requested: list[CurrencyAmount] = Field(default_factory=list)


class AnalyticsOverview(ApiModel):
    """Aggregate data only: this contract deliberately has no employee identities."""

    generated_at: datetime
    period_months: int = Field(ge=1, le=24)
    scope: str = Field(pattern=r"^(organization|managed|personal)$")
    summary: AnalyticsSummary
    report_statuses: list[StatusCount] = Field(default_factory=list)
    spending_by_category: list[CategorySpend] = Field(default_factory=list)
    monthly_spend: list[MonthlySpend] = Field(default_factory=list)
