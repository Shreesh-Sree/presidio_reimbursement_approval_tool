"""Versioned input and output contracts for the isolated receipt service."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
import re
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


_SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
_SCOPE_PATTERN = re.compile(r"^[A-Za-z0-9:_\-.]{3,128}$")


class TextSource(StrEnum):
    """How optional text reached this service."""

    NOT_PROVIDED = "not_provided"
    CALLER_EXTRACTED = "caller_extracted"


class FindingSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class FindingCode(StrEnum):
    UNSUPPORTED_MEDIA_TYPE = "unsupported_media_type"
    FILE_TOO_LARGE = "file_too_large"
    RECEIPT_REQUIRED_MISSING = "receipt_required_missing"
    DUPLICATE_RECEIPT_DIGEST = "duplicate_receipt_digest"
    SUSPICIOUS_EMBEDDED_INSTRUCTION = "suspicious_embedded_instruction"


class ReceiptDocumentInput(BaseModel):
    """Metadata and optional caller-extracted plain text for one receipt.

    File bytes, URLs, filenames, OCR configuration, and core database
    identifiers are deliberately not part of this contract.
    """

    model_config = ConfigDict(extra="forbid")

    sha256_digest: str = Field(
        description="Lowercase SHA-256 digest of the uploaded receipt file.",
        min_length=64,
        max_length=64,
    )
    media_type: str = Field(min_length=3, max_length=100)
    size_bytes: int = Field(ge=0, le=1024 * 1024 * 1024)
    supplied_text: str | None = Field(
        default=None,
        max_length=100_000,
        description="Optional plain text already extracted by a trusted caller.",
    )
    text_source: TextSource = TextSource.NOT_PROVIDED

    @field_validator("sha256_digest")
    @classmethod
    def normalise_digest(cls, value: str) -> str:
        digest = value.strip().lower()
        if not _SHA256_PATTERN.fullmatch(digest):
            raise ValueError("sha256_digest must be a 64-character hexadecimal SHA-256 digest")
        return digest

    @field_validator("media_type")
    @classmethod
    def normalise_media_type(cls, value: str) -> str:
        media_type = value.strip().lower()
        if "/" not in media_type:
            raise ValueError("media_type must be a valid MIME type")
        return media_type

    @field_validator("supplied_text")
    @classmethod
    def normalise_supplied_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def validate_text_source(self) -> "ReceiptDocumentInput":
        has_text = bool(self.supplied_text and self.supplied_text.strip())
        if has_text and self.text_source != TextSource.CALLER_EXTRACTED:
            raise ValueError("supplied_text requires text_source='caller_extracted'")
        if not has_text and self.text_source != TextSource.NOT_PROVIDED:
            raise ValueError("text_source='caller_extracted' requires non-empty supplied_text")
        return self


class ReceiptPolicyContext(BaseModel):
    """The caller's frozen policy facts; this service never reads policy tables."""

    model_config = ConfigDict(extra="forbid")

    expense_amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    receipt_required_at_or_above: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=14,
        decimal_places=2,
    )

    @field_validator("currency")
    @classmethod
    def normalise_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        currency = value.strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", currency):
            raise ValueError("currency must be a three-letter ISO-style code")
        return currency


class ReceiptAnalysisRequest(BaseModel):
    """An event-shaped request suitable for an asynchronous core dispatcher."""

    model_config = ConfigDict(extra="forbid")

    event_id: UUID = Field(default_factory=uuid4)
    event_type: Literal["receipt.analysis.requested"] = "receipt.analysis.requested"
    event_version: Literal["1.0"] = "1.0"
    organization_scope: str = Field(
        min_length=3,
        max_length=128,
        description="Opaque tenant/organization scope; do not send a display name.",
    )
    receipt: ReceiptDocumentInput | None = None
    policy: ReceiptPolicyContext = Field(default_factory=ReceiptPolicyContext)

    @field_validator("organization_scope")
    @classmethod
    def validate_organization_scope(cls, value: str) -> str:
        scope = value.strip()
        if not _SCOPE_PATTERN.fullmatch(scope):
            raise ValueError("organization_scope must be an opaque identifier")
        return scope


class ReceiptFinding(BaseModel):
    """A deterministic finding with only safe, non-content details."""

    model_config = ConfigDict(extra="forbid")

    code: FindingCode
    severity: FindingSeverity
    message: str
    details: dict[str, str | int | bool] = Field(default_factory=dict)


class ReceiptEvidence(BaseModel):
    """Best-effort evidence derived in memory from caller-supplied plain text."""

    model_config = ConfigDict(extra="forbid")

    merchant_candidates: tuple[str, ...] = ()
    date_candidates: tuple[str, ...] = ()
    amount_candidates: tuple[str, ...] = ()
    masked_receipt_number_candidates: tuple[str, ...] = ()


class GuardrailResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    receipt_present: bool
    media_type_allowed: bool | None
    size_within_limit: bool | None
    max_file_bytes: int
    allowed_media_types: tuple[str, ...]


class DeduplicationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    duplicate_within_organization: bool
    prior_seen_count: int
    total_seen_count: int


class OcrDisclosure(BaseModel):
    """Explicitly state that this release does not perform OCR."""

    model_config = ConfigDict(extra="forbid")

    performed: bool = False
    available_in_this_service: bool = False
    text_source: TextSource
    message: str


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok", "ready", "not_ready"]
    service: Literal["receipt-intelligence"]


class ReceiptAnalysisResponse(BaseModel):
    """The deterministic response; no raw text is echoed or persisted."""

    model_config = ConfigDict(extra="forbid")

    analysis_id: UUID = Field(default_factory=uuid4)
    event_id: UUID
    correlation_id: str
    guardrails: GuardrailResult
    deduplication: DeduplicationResult | None
    evidence: ReceiptEvidence
    ocr: OcrDisclosure
    findings: tuple[ReceiptFinding, ...]
