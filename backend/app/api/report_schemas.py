"""Validated JSON contracts for reports, approvals, and comments."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReportApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, str_strip_whitespace=True)


class ReportCreateInput(ReportApiModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10_000)
    start_date: date | None = None
    end_date: date | None = None
    currency: str = Field(default="INR", min_length=3, max_length=10)

    @model_validator(mode="after")
    def dates_are_ordered(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        return self


class ReportUpdateInput(ReportApiModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10_000)
    start_date: date | None = None
    end_date: date | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=10)


class LineItemCreateInput(ReportApiModel):
    category_id: UUID | None = None
    category_name: str | None = Field(default=None, max_length=150)
    vendor_id: UUID | None = None
    vendor_name: str | None = Field(default=None, max_length=255)
    merchant_name: str | None = Field(default=None, max_length=255)
    amount: Decimal = Field(gt=0, max_digits=16, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=10)
    description: str | None = Field(default=None, max_length=10_000)
    expense_date: date

    @model_validator(mode="after")
    def category_is_present(self):
        if self.category_id is None and not self.category_name:
            raise ValueError("category_id is required")
        return self


class LineItemUpdateInput(ReportApiModel):
    category_id: UUID | None = None
    category_name: str | None = Field(default=None, max_length=150)
    vendor_id: UUID | None = None
    vendor_name: str | None = Field(default=None, max_length=255)
    merchant_name: str | None = Field(default=None, max_length=255)
    amount: Decimal | None = Field(default=None, gt=0, max_digits=16, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=10)
    description: str | None = Field(default=None, max_length=10_000)
    expense_date: date | None = None
    remarks: str | None = Field(default=None, max_length=10_000)


class ApprovalActionInput(ReportApiModel):
    remarks: str | None = Field(default=None, max_length=10_000)


class CommentInput(ReportApiModel):
    body: str = Field(min_length=1, max_length=10_000)
    visibility: str = Field(default="employee", pattern="^(all|employee|internal)$")
    parent_comment_id: UUID | None = None
