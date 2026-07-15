"""Public request contracts for administrator-managed workflow rules."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.api.schemas import ApiModel


class WorkflowConditionsInput(ApiModel):
    min_total: Decimal | None = Field(default=None, ge=0, max_digits=16, decimal_places=2)
    max_total: Decimal | None = Field(default=None, ge=0, max_digits=16, decimal_places=2)
    department_id: UUID | None = None
    currency_code: str | None = Field(default=None, min_length=3, max_length=10)

    @field_validator("currency_code")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None

    @model_validator(mode="after")
    def validate_thresholds(self):
        if self.min_total is not None and self.max_total is not None and self.min_total > self.max_total:
            raise ValueError("minimum total cannot exceed maximum total")
        return self


class WorkflowStepInput(ApiModel):
    manager_level: int | None = Field(default=None, ge=1, le=10)
    user_id: UUID | None = None
    role_code: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("role_code")
    @classmethod
    def normalize_role_code(cls, value: str | None) -> str | None:
        return value.strip().lower() if value is not None else None

    @model_validator(mode="after")
    def choose_one_selector(self):
        selected = sum(
            value is not None
            for value in (self.manager_level, self.user_id, self.role_code)
        )
        if selected != 1:
            raise ValueError("choose exactly one of manager_level, user_id, or role_code")
        return self


class WorkflowRuleCreateInput(ApiModel):
    name: str = Field(min_length=1, max_length=255)
    conditions: WorkflowConditionsInput = Field(default_factory=WorkflowConditionsInput)
    approval_chain: list[WorkflowStepInput] = Field(min_length=1, max_length=10)
    priority: int = Field(default=100, ge=0, le=100_000)
    is_active: bool = True


class WorkflowRuleUpdateInput(ApiModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    conditions: WorkflowConditionsInput | None = None
    approval_chain: list[WorkflowStepInput] | None = Field(default=None, min_length=1, max_length=10)
    priority: int | None = Field(default=None, ge=0, le=100_000)
    is_active: bool | None = None
