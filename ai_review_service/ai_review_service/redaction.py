"""PII minimisation utilities for the AI-service boundary.

The core application should publish only opaque IDs and receipt digests.  These
helpers are a second line of defence: they remove common direct identifiers
from free-text fields before a job is persisted or any prompt is assembled.
"""

from __future__ import annotations

from hashlib import sha256
import hmac
import json
import re
from typing import Any

from .contracts import (
    ExpenseLineSnapshot,
    ExpenseReviewRequested,
    NarrativeDraft,
    ProviderReviewContext,
    ReviewFinding,
    RuleEvaluation,
)


_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d .()\-]{7,}\d)(?!\w)")
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CARD = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
_URL = re.compile(r"\bhttps?://[^\s]+", re.IGNORECASE)
_WHITESPACE = re.compile(r"\s+")


def redact_text(value: str | None, *, limit: int = 512) -> str | None:
    """Redact common direct identifiers and bound retained free text.

    This intentionally does not try to infer personal names.  The event
    contract therefore uses opaque references and vendor/category *codes*, and
    excludes user profiles and receipt/document text altogether.
    """

    if value is None:
        return None
    redacted = _EMAIL.sub("[email redacted]", value)
    redacted = _SSN.sub("[government-id redacted]", redacted)
    redacted = _CARD.sub("[payment-number redacted]", redacted)
    redacted = _PHONE.sub("[phone redacted]", redacted)
    redacted = _URL.sub("[url redacted]", redacted)
    redacted = _WHITESPACE.sub(" ", redacted).strip()
    return redacted[:limit] if redacted else None


def pseudonymize(value: str, *, secret: str) -> str:
    """Create a stable non-reversible reference if an upstream alias is needed."""

    if not secret:
        raise ValueError("a non-empty secret is required for pseudonymization")
    digest = hmac.new(secret.encode("utf-8"), value.encode("utf-8"), sha256).hexdigest()
    return f"anon:{digest[:32]}"


def minimise_event(event: ExpenseReviewRequested) -> ExpenseReviewRequested:
    """Return the safe event representation that may be stored by this service."""

    items = tuple(
        item.model_copy(
            update={
                "description_excerpt": redact_text(item.description_excerpt),
                "vendor_code": redact_text(item.vendor_code, limit=128),
            }
        )
        for item in event.items
    )
    # Receipt digest is useful for duplicate checks.  File names, URLs, OCR text,
    # pixels, and object-store references are deliberately not represented.
    return event.model_copy(update={"items": items})


def _safe_finding(finding: ReviewFinding) -> ReviewFinding:
    """Strip line identifiers before handing a finding to a model provider."""

    safe_evidence: dict[str, Any] = {}
    for key, value in finding.evidence.items():
        safe_key = redact_text(key, limit=64)
        if safe_key:
            safe_evidence[safe_key] = redact_text(value, limit=160) if isinstance(value, str) else value
    return ReviewFinding(
        finding_type=finding.finding_type,
        severity=finding.severity,
        message=redact_text(finding.message, limit=500) or "Policy or anomaly finding detected.",
        category_code=redact_text(finding.category_code, limit=64),
        policy_rule_ref=redact_text(finding.policy_rule_ref, limit=128),
        evidence=safe_evidence,
    )


def provider_context(evaluation: RuleEvaluation, *, item_count: int) -> ProviderReviewContext:
    """Build the least-privilege generative-provider payload.

    The returned object has no report ID, tenant/user reference, line ID,
    vendor, description, receipt digest, file link, or raw policy document.
    """

    return ProviderReviewContext(
        report_total=evaluation.report_total,
        currency=evaluation.currency,
        line_item_count=item_count,
        category_totals=evaluation.category_totals,
        findings=tuple(_safe_finding(finding) for finding in evaluation.findings),
        risk_level=evaluation.risk_level,
    )


def provider_prompt(context: ProviderReviewContext) -> str:
    """Serialize only the minimized, non-identifying review facts for an LLM."""

    facts = {
        "report_total": str(context.report_total),
        "currency": context.currency,
        "line_item_count": context.line_item_count,
        "category_totals": {key: str(value) for key, value in context.category_totals.items()},
        "risk_level": context.risk_level.value,
        "findings": [
            {
                "type": finding.finding_type.value,
                "severity": finding.severity.value,
                "category": finding.category_code,
                "message": finding.message,
                "evidence": {key: str(value) for key, value in finding.evidence.items()},
            }
            for finding in context.findings
        ],
    }
    return (
        "You are an advisory expense-review assistant. Use only these minimized "
        "facts. Do not infer identities or make a final workflow decision. Draft a "
        "concise, factual approval summary and call out findings for a human reviewer.\n\n"
        + json.dumps(facts, sort_keys=True, separators=(",", ":"))
    )


def redact_narrative(draft: NarrativeDraft) -> NarrativeDraft:
    """Defensively redact generated text before it is returned or persisted."""

    return draft.model_copy(
        update={
            "summary": redact_text(draft.summary, limit=2_000) or "Advisory review completed.",
            "key_insights": tuple(
                insight
                for raw in draft.key_insights
                if (insight := redact_text(raw, limit=400))
            ),
        }
    )
