"""Strict public contracts for the isolated policy assistant."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


_OPAQUE_REF = re.compile(r"^[a-z][a-z0-9]*(?:[-_][a-z0-9][a-z0-9_-]*)+$")
_EMAIL_LIKE = re.compile(r"@|\b(?:ssn|passport|email|phone)\b", re.IGNORECASE)


def _validate_opaque_ref(value: object, *, kind: str, prefixes: tuple[str, ...]) -> str:
    """Permit durable opaque references, never names, addresses, or URLs."""

    reference = str(value or "").strip()
    if not reference or len(reference) > 96:
        raise ValueError(f"{kind} must be a compact opaque reference")
    if not _OPAQUE_REF.fullmatch(reference) or _EMAIL_LIKE.search(reference):
        raise ValueError(f"{kind} must be an opaque reference, not a raw identifier")
    if not reference.startswith(tuple(f"{prefix}-" for prefix in prefixes) + tuple(
        f"{prefix}_" for prefix in prefixes
    )):
        expected = ", ".join(f"{prefix}-…" for prefix in prefixes)
        raise ValueError(f"{kind} must use an opaque namespace such as {expected}")
    return reference


class PolicyScope(BaseModel):
    """Tenant and policy version boundary shared by every persisted operation."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    tenant_ref: str = Field(min_length=4, max_length=96)
    policy_version_ref: str = Field(min_length=4, max_length=96)

    @field_validator("tenant_ref")
    @classmethod
    def validate_tenant_ref(cls, value: object) -> str:
        return _validate_opaque_ref(value, kind="tenant_ref", prefixes=("tenant", "org", "workspace"))

    @field_validator("policy_version_ref")
    @classmethod
    def validate_policy_version_ref(cls, value: object) -> str:
        return _validate_opaque_ref(value, kind="policy_version_ref", prefixes=("policy", "version"))


class PolicyDocumentIndexRequest(PolicyScope):
    """A policy document body, indexed only within its explicit policy scope."""

    document_ref: str = Field(min_length=4, max_length=96)
    content: str = Field(min_length=1, max_length=250_000)

    @field_validator("document_ref")
    @classmethod
    def validate_document_ref(cls, value: object) -> str:
        return _validate_opaque_ref(value, kind="document_ref", prefixes=("document", "doc"))

    @field_validator("content")
    @classmethod
    def reject_null_bytes(cls, value: str) -> str:
        if "\x00" in value:
            raise ValueError("content cannot contain null bytes")
        return value


class PolicyDocumentIndexResponse(PolicyScope):
    document_ref: str
    document_digest: str
    chunk_count: int
    injection_flags: tuple[str, ...]


class PolicyAskRequest(PolicyScope):
    question: str = Field(min_length=1, max_length=10_000)
    top_k: int | None = Field(default=None, ge=1, le=8)

    @field_validator("question")
    @classmethod
    def reject_null_question(cls, value: str) -> str:
        if "\x00" in value:
            raise ValueError("question cannot contain null bytes")
        return value.strip()


class PolicyCitation(PolicyScope):
    document_ref: str
    source_chunk_id: str
    excerpt: str
    similarity: float


class PolicyAskResponse(BaseModel):
    """Every evidence-bearing response includes its exact source chunk citations."""

    answer: str
    evidence_found: bool
    citations: tuple[PolicyCitation, ...]
