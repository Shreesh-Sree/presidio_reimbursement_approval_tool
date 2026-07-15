"""Versioned, PII-minimized contracts owned by the AI review service.

These types are intentionally independent of the reimbursement application's
ORM.  Upstream code should publish an event after submission and never pass a
database session, a receipt file, a user name, email address, or raw document
content into this service.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import StrEnum
import re
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ContractModel(BaseModel):
    """Strict base model shared by all public service contracts."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


_OPAQUE_REFERENCE = re.compile(r"^[A-Za-z0-9_.:-]{3,128}$")
_CODE = re.compile(r"^[A-Z0-9][A-Z0-9_.:-]{0,127}$")
_RECEIPT_DIGEST = re.compile(r"^(?:sha256:)?[a-fA-F0-9]{32,128}$")


def validate_opaque_reference(value: str) -> str:
    """Accept stable pseudonyms/UUIDs but reject obvious direct identifiers."""

    if "@" in value or not _OPAQUE_REFERENCE.fullmatch(value):
        raise ValueError(
            "reference must be an opaque UUID or pseudonym; do not send a name, email, or phone number"
        )
    return value


def normalise_code(value: str | None, *, field_name: str) -> str | None:
    """Require classification codes rather than labels/free text at this boundary."""

    if value is None:
        return None
    normalized = value.upper()
    if not _CODE.fullmatch(normalized):
        raise ValueError(f"{field_name} must be an opaque code, not a display label or free-text value")
    return normalized


class FindingType(StrEnum):
    POLICY_LIMIT_EXCEEDED = "policy_limit_exceeded"
    POLICY_REPORT_CAP_EXCEEDED = "policy_report_cap_exceeded"
    MISSING_RECEIPT = "missing_receipt"
    DISALLOWED_VENDOR = "disallowed_vendor"
    VENDOR_CAP_EXCEEDED = "vendor_cap_exceeded"
    UNCONFIGURED_CATEGORY = "unconfigured_category"
    POTENTIAL_DUPLICATE = "potential_duplicate"
    UNUSUAL_SPEND = "unusual_spend"


class FindingSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ReviewRecommendation(StrEnum):
    APPROVE = "approve"
    REQUEST_INFORMATION = "request_information"
    REJECT = "reject"


class ProviderStatus(StrEnum):
    RULE_BASED = "rule_based"
    GENERATED = "generated"
    FALLBACK = "fallback"


class ReviewJobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    RETRY_PENDING = "retry_pending"
    COMPLETED = "completed"
    FAILED = "failed"


class HumanDispositionAction(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    SEND_BACK = "send_back"
    ACKNOWLEDGE = "acknowledge"
    OVERRIDE_RECOMMENDATION = "override_recommendation"


class ReceiptEvidence(ContractModel):
    """Receipt metadata only; receipt bytes and URLs never enter this service."""

    attached: bool = False
    digest: str | None = Field(default=None, min_length=16, max_length=128)

    @field_validator("digest", mode="after")
    @classmethod
    def validate_digest(cls, value: str | None) -> str | None:
        if value is not None and not _RECEIPT_DIGEST.fullmatch(value):
            raise ValueError("receipt digest must be a SHA-256-style digest, never a file name or URL")
        return value.lower() if value else value


class ExpenseLineSnapshot(ContractModel):
    """Minimum data needed for deterministic policy/anomaly checks."""

    line_id: UUID
    expense_date: date
    category_code: str = Field(min_length=1, max_length=64)
    subcategory_code: str | None = Field(default=None, max_length=64)
    vendor_code: str | None = Field(default=None, max_length=128)
    amount: Decimal = Field(gt=Decimal("0"), max_digits=14, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3)
    description_excerpt: str | None = Field(default=None, max_length=512)
    receipt: ReceiptEvidence = Field(default_factory=ReceiptEvidence)

    @field_validator("category_code", "subcategory_code", "vendor_code", mode="after")
    @classmethod
    def normalise_codes(cls, value: str | None) -> str | None:
        return normalise_code(value, field_name="category, subcategory, and vendor codes")

    @field_validator("currency", mode="after")
    @classmethod
    def normalise_currency(cls, value: str) -> str:
        return value.upper()


class PolicyRuleSnapshot(ContractModel):
    """A policy snapshot supplied by the core service at submit time."""

    rule_ref: str = Field(min_length=1, max_length=128)
    category_code: str = Field(min_length=1, max_length=64)
    subcategory_code: str | None = Field(default=None, max_length=64)
    max_per_item: Decimal | None = Field(default=None, gt=Decimal("0"), max_digits=14, decimal_places=2)
    max_per_report: Decimal | None = Field(default=None, gt=Decimal("0"), max_digits=14, decimal_places=2)
    receipt_required_at_or_above: Decimal | None = Field(
        default=None, gt=Decimal("0"), max_digits=14, decimal_places=2
    )
    allowed_vendor_codes: tuple[str, ...] = ()
    vendor_caps: dict[str, Decimal] = Field(default_factory=dict)

    @field_validator("category_code", "subcategory_code", mode="after")
    @classmethod
    def normalise_category_codes(cls, value: str | None) -> str | None:
        return normalise_code(value, field_name="category and subcategory codes")

    @field_validator("allowed_vendor_codes", mode="after")
    @classmethod
    def normalise_allowed_vendors(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
            normalise_code(value, field_name="allowed vendor code") or "" for value in values
        )

    @field_validator("vendor_caps", mode="after")
    @classmethod
    def normalise_vendor_caps(cls, values: dict[str, Decimal]) -> dict[str, Decimal]:
        return {
            normalise_code(key, field_name="vendor cap code") or "": value
            for key, value in values.items()
        }


class PolicySnapshot(ContractModel):
    policy_version_ref: str = Field(min_length=1, max_length=128)
    rules: tuple[PolicyRuleSnapshot, ...] = Field(min_length=1)


class HistoricalCategoryBaseline(ContractModel):
    """Aggregate historical data, never an employee's individual claims."""

    category_code: str = Field(min_length=1, max_length=64)
    average_amount: Decimal = Field(gt=Decimal("0"), max_digits=14, decimal_places=2)
    sample_size: int = Field(ge=0, le=100_000)
    alert_multiplier: Decimal = Field(default=Decimal("2.5"), gt=Decimal("1"), max_digits=5, decimal_places=2)

    @field_validator("category_code", mode="after")
    @classmethod
    def normalise_category_code(cls, value: str) -> str:
        return normalise_code(value, field_name="category code") or ""


class ExpenseReviewRequested(ContractModel):
    """Event emitted by the core service after an expense report is submitted.

    ``submitter_ref`` and ``tenant_ref`` are opaque IDs (UUIDs or HMAC-derived
    aliases).  The service rejects obvious identifiers such as email addresses.
    """

    event_id: UUID = Field(default_factory=uuid4)
    event_type: Literal["expense_report.submitted", "expense_report.resubmitted"] = "expense_report.submitted"
    event_version: Literal["1.0"] = "1.0"
    occurred_at: datetime = Field(default_factory=utc_now)
    report_id: UUID
    tenant_ref: str = Field(min_length=3, max_length=128)
    submitter_ref: str = Field(min_length=3, max_length=128)
    items: tuple[ExpenseLineSnapshot, ...] = Field(min_length=1, max_length=500)
    policy: PolicySnapshot
    historical_baselines: tuple[HistoricalCategoryBaseline, ...] = ()
    known_receipt_digests: tuple[str, ...] = ()

    @field_validator("tenant_ref", "submitter_ref", mode="after")
    @classmethod
    def validate_references(cls, value: str) -> str:
        return validate_opaque_reference(value)

    @field_validator("known_receipt_digests", mode="after")
    @classmethod
    def validate_known_receipt_digests(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized: list[str] = []
        for value in values:
            if not _RECEIPT_DIGEST.fullmatch(value):
                raise ValueError("known receipt values must be digests, never file names or URLs")
            normalized.append(value.lower())
        return tuple(normalized)


FindingEvidenceValue = str | int | Decimal | bool | None


class ReviewFinding(ContractModel):
    id: UUID = Field(default_factory=uuid4)
    finding_type: FindingType
    severity: FindingSeverity
    message: str = Field(min_length=1, max_length=500)
    line_id: UUID | None = None
    category_code: str | None = Field(default=None, max_length=64)
    policy_rule_ref: str | None = Field(default=None, max_length=128)
    evidence: dict[str, FindingEvidenceValue] = Field(default_factory=dict)


class RuleEvaluation(ContractModel):
    report_total: Decimal = Field(ge=Decimal("0"), max_digits=14, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3)
    category_totals: dict[str, Decimal]
    findings: tuple[ReviewFinding, ...]
    risk_level: FindingSeverity


class ProviderReviewContext(ContractModel):
    """The only data supplied to a generative provider; it excludes PII/IDs."""

    report_total: Decimal = Field(ge=Decimal("0"))
    currency: str = Field(min_length=3, max_length=3)
    line_item_count: int = Field(ge=0)
    category_totals: dict[str, Decimal]
    findings: tuple[ReviewFinding, ...]
    risk_level: FindingSeverity


class NarrativeDraft(ContractModel):
    summary: str = Field(min_length=1, max_length=2_000)
    key_insights: tuple[str, ...] = Field(default=(), max_length=10)
    recommendation: ReviewRecommendation


class ProviderOutcome(ContractModel):
    provider_name: str = Field(min_length=1, max_length=128)
    status: ProviderStatus
    attempts: int = Field(ge=0)
    used_fallback: bool = False
    failure_reason: str | None = Field(default=None, max_length=500)
    narrative: NarrativeDraft


class HumanReviewGate(ContractModel):
    """Makes the service's advisory-only boundary explicit in every result."""

    required: Literal[True] = True
    automated_action_taken: Literal[False] = False
    allowed_actions: tuple[HumanDispositionAction, ...] = (
        HumanDispositionAction.APPROVE,
        HumanDispositionAction.REJECT,
        HumanDispositionAction.SEND_BACK,
        HumanDispositionAction.ACKNOWLEDGE,
        HumanDispositionAction.OVERRIDE_RECOMMENDATION,
    )
    message: str = "AI recommendations are advisory; an authorized human must make the workflow decision."


class ReviewResult(ContractModel):
    id: UUID = Field(default_factory=uuid4)
    job_id: UUID
    event_id: UUID
    report_id: UUID
    created_at: datetime = Field(default_factory=utc_now)
    evaluation: RuleEvaluation
    summary: str = Field(min_length=1, max_length=2_000)
    key_insights: tuple[str, ...] = Field(default=(), max_length=10)
    recommendation: ReviewRecommendation
    provider: ProviderOutcome
    human_review: HumanReviewGate = Field(default_factory=HumanReviewGate)


class ReviewJob(ContractModel):
    id: UUID = Field(default_factory=uuid4)
    event: ExpenseReviewRequested
    status: ReviewJobStatus = ReviewJobStatus.QUEUED
    attempt_count: int = Field(default=0, ge=0)
    max_attempts: int = Field(default=3, ge=1, le=10)
    result: ReviewResult | None = None
    failure_reason: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ReviewDispositionRequest(ContractModel):
    """A human's workflow verdict recorded separately from the AI result."""

    reviewer_ref: str = Field(min_length=3, max_length=128)
    action: HumanDispositionAction
    remarks: str | None = Field(default=None, max_length=1_000)
    finding_ids: tuple[UUID, ...] = ()

    @field_validator("reviewer_ref", mode="after")
    @classmethod
    def validate_reviewer_reference(cls, value: str) -> str:
        return validate_opaque_reference(value)


class ReviewDisposition(ContractModel):
    id: UUID = Field(default_factory=uuid4)
    job_id: UUID
    reviewer_ref: str
    action: HumanDispositionAction
    remarks: str | None = None
    finding_ids: tuple[UUID, ...] = ()
    decided_at: datetime = Field(default_factory=utc_now)
