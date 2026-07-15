"""Contracts for an approver's temporary delegation settings."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.api.schemas import ApiModel


class DelegationCreateInput(ApiModel):
    delegate_user_id: UUID
    start_date: datetime
    end_date: datetime
    scope: str = Field(default="approval", min_length=1, max_length=20)
    remarks: str | None = Field(default=None, max_length=2_000)

    @field_validator("scope")
    @classmethod
    def normalize_scope(cls, value: str) -> str:
        return value.strip().lower()

    @model_validator(mode="after")
    def validate_window(self):
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self


class DelegationResponse(ApiModel):
    id: UUID
    delegator_user_id: UUID
    delegate_user_id: UUID
    delegate_name: str | None = None
    start_date: datetime
    end_date: datetime
    scope: str
    is_active: bool
    remarks: str | None = None
    created_at: datetime
    updated_at: datetime
