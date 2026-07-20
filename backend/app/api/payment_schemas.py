"""Request contracts for finance-owned reimbursement payment operations."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PaymentApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PaymentBatchCreateInput(PaymentApiModel):
    payment_ids: list[UUID] = Field(min_length=1, max_length=500)
    remarks: str | None = Field(default=None, max_length=1_000)


class PaymentBatchStatusInput(PaymentApiModel):
    status: str = Field(pattern="^(created|exported|completed|cancelled)$")
    remarks: str | None = Field(default=None, max_length=1_000)


class PaymentPaidInput(PaymentApiModel):
    provider_reference: str = Field(min_length=1, max_length=150)
    payment_date: date | None = None
    remarks: str | None = Field(default=None, max_length=1_000)


class PaymentFailedInput(PaymentApiModel):
    failure_reason: str = Field(min_length=1, max_length=1_000)
    remarks: str | None = Field(default=None, max_length=1_000)
