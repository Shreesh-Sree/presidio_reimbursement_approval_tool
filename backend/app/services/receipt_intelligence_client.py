"""Metadata-only HTTP boundary for the isolated receipt-intelligence service.

The core API deliberately does not import the service package or its SQLite
store.  This module accepts only opaque-able identifiers and receipt metadata;
it never reads object storage, receives filenames, or accepts extracted text.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
import re
import uuid
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import get_settings


_SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
_CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")


class ReceiptIntelligenceError(RuntimeError):
    """A safe failure raised by the optional receipt-intelligence boundary."""


@dataclass(frozen=True)
class ReceiptAnalysisContext:
    """Opaque correlation references returned to the authorized caller only."""

    organization_ref: str
    report_ref: str
    item_ref: str
    attachment_ref: str | None
    event_id: str


@dataclass(frozen=True)
class ReceiptAnalysisResult:
    """Advisory response; it is never persisted in the core database."""

    context: ReceiptAnalysisContext
    analysis: dict[str, Any]


def _service_url() -> str | None:
    value = (os.getenv("RECEIPT_INTELLIGENCE_SERVICE_URL", "").strip() or get_settings().receipt_intelligence_service_url.strip()).rstrip("/")
    return value or None


def _timeout() -> float:
    try:
        return max(0.1, min(30.0, float(os.getenv("RECEIPT_INTELLIGENCE_TIMEOUT_SECONDS", "") or get_settings().receipt_intelligence_timeout_seconds)))
    except ValueError:
        return 4.0


def _uuid(value: uuid.UUID | str, *, label: str) -> uuid.UUID:
    try:
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ReceiptIntelligenceError(f"Receipt intelligence received an invalid {label} reference") from exc


def _opaque_ref(prefix: str, value: uuid.UUID | str) -> str:
    """Derive a stable, non-reversible reference without disclosing core IDs."""

    identifier = _uuid(value, label=prefix)
    digest = hashlib.sha256(f"presidio:receipt-intelligence:{prefix}:{identifier.hex}".encode("utf-8")).hexdigest()
    return f"{prefix}-{digest[:32]}"


def _decimal_string(value: Decimal | float | int | str, *, label: str) -> str:
    try:
        normalized = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ReceiptIntelligenceError(f"Receipt intelligence received an invalid {label}") from exc
    if not normalized.is_finite() or normalized < 0:
        raise ReceiptIntelligenceError(f"Receipt intelligence received an invalid {label}")
    return f"{normalized.quantize(Decimal('0.01')):.2f}"


def _receipt_payload(
    *,
    checksum: str | None,
    mime_type: str | None,
    size_bytes: int | None,
) -> dict[str, Any] | None:
    values = (checksum, mime_type, size_bytes)
    if all(value is None for value in values):
        return None
    if any(value is None for value in values):
        raise ReceiptIntelligenceError("Receipt intelligence received incomplete receipt metadata")
    assert checksum is not None and mime_type is not None and size_bytes is not None
    digest = checksum.strip().lower()
    media_type = mime_type.strip().lower()
    if not _SHA256_PATTERN.fullmatch(digest) or "/" not in media_type or not 3 <= len(media_type) <= 100:
        raise ReceiptIntelligenceError("Receipt intelligence received invalid receipt metadata")
    if not isinstance(size_bytes, int) or isinstance(size_bytes, bool) or not 0 <= size_bytes <= 1024 * 1024 * 1024:
        raise ReceiptIntelligenceError("Receipt intelligence received invalid receipt metadata")
    return {
        "sha256_digest": digest,
        "media_type": media_type,
        "size_bytes": size_bytes,
    }


def _request(method: str, path: str, payload: dict[str, Any], request_id: str) -> dict[str, Any]:
    base_url = _service_url()
    if not base_url:
        raise ReceiptIntelligenceError("Receipt intelligence service is not configured")
    token = os.getenv("RECEIPT_INTELLIGENCE_SERVICE_TOKEN", "").strip() or get_settings().receipt_intelligence_service_token.strip()
    if not token:
        raise ReceiptIntelligenceError("Receipt intelligence service credentials are not configured")
    request = Request(
        f"{base_url}{path}",
        data=json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8"),
        method=method,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Request-ID": request_id,
        },
    )
    try:
        with urlopen(request, timeout=_timeout()) as response:  # nosec B310: deployment-owned internal endpoint
            decoded = response.read().decode("utf-8")
    except HTTPError as exc:
        if exc.code in {401, 403}:
            raise ReceiptIntelligenceError("Receipt intelligence service authentication failed") from exc
        if exc.code == 422:
            raise ReceiptIntelligenceError("Receipt intelligence service rejected receipt metadata") from exc
        raise ReceiptIntelligenceError("Receipt intelligence service is unavailable") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise ReceiptIntelligenceError("Receipt intelligence service is unavailable") from exc
    try:
        body = json.loads(decoded)
    except json.JSONDecodeError as exc:
        raise ReceiptIntelligenceError("Receipt intelligence service returned invalid JSON") from exc
    if not isinstance(body, dict):
        raise ReceiptIntelligenceError("Receipt intelligence service returned an invalid payload")
    return body


def analyze_receipt(
    *,
    organization_id: uuid.UUID | str,
    report_id: uuid.UUID | str,
    item_id: uuid.UUID | str,
    attachment_id: uuid.UUID | str | None,
    receipt_checksum: str | None,
    receipt_mime_type: str | None,
    receipt_size_bytes: int | None,
    expense_amount: Decimal | float | int | str,
    currency: str,
    receipt_required_at_or_above: Decimal | float | int | str | None,
    supplied_text: str | None = None,
    text_source: str = "not_provided",
) -> ReceiptAnalysisResult:
    """Request a one-off advisory check without transmitting core identifiers.

    ``report_id``, ``item_id``, and ``attachment_id`` only derive local opaque
    correlation references.  The remote service receives the tenant scope,
    an opaque deterministic event ID, metadata, and frozen policy facts.
    """

    context = ReceiptAnalysisContext(
        organization_ref=_opaque_ref("tenant", organization_id),
        report_ref=_opaque_ref("report", report_id),
        item_ref=_opaque_ref("item", item_id),
        attachment_ref=_opaque_ref("attachment", attachment_id) if attachment_id is not None else None,
        event_id="",
    )
    event_id = uuid.uuid5(
        uuid.NAMESPACE_URL,
        ":".join(
            reference
            for reference in (
                context.organization_ref,
                context.report_ref,
                context.item_ref,
                context.attachment_ref,
            )
            if reference is not None
        ),
    )
    context = ReceiptAnalysisContext(
        organization_ref=context.organization_ref,
        report_ref=context.report_ref,
        item_ref=context.item_ref,
        attachment_ref=context.attachment_ref,
        event_id=str(event_id),
    )
    normalized_currency = currency.strip().upper()
    if not _CURRENCY_PATTERN.fullmatch(normalized_currency):
        raise ReceiptIntelligenceError("Receipt intelligence received an invalid currency")

    receipt_payload = _receipt_payload(
        checksum=receipt_checksum,
        mime_type=receipt_mime_type,
        size_bytes=receipt_size_bytes,
    )
    if receipt_payload is not None and supplied_text:
        receipt_payload["supplied_text"] = supplied_text[:100_000]
        receipt_payload["text_source"] = text_source
    payload: dict[str, Any] = {
        "event_id": context.event_id,
        "event_type": "receipt.analysis.requested",
        "event_version": "1.0",
        "organization_scope": context.organization_ref,
        "receipt": receipt_payload,
        "policy": {
            "expense_amount": _decimal_string(expense_amount, label="expense amount"),
            "currency": normalized_currency,
            "receipt_required_at_or_above": (
                _decimal_string(receipt_required_at_or_above, label="receipt threshold")
                if receipt_required_at_or_above is not None
                else None
            ),
        },
    }
    analysis = _request("POST", "/v1/analyze", payload, f"receipt-{event_id.hex}")
    return ReceiptAnalysisResult(context=context, analysis=analysis)


def extract_receipt_text(*, content: bytes, media_type: str) -> str:
    """Use the isolated OCR endpoint; image bytes are never persisted by it."""

    if media_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise ReceiptIntelligenceError("OCR currently supports JPEG, PNG, and WebP receipt images")
    response = _request(
        "POST",
        "/v1/ocr",
        {"media_type": media_type, "content_base64": base64.b64encode(content).decode("ascii")},
        f"ocr-{uuid.uuid4().hex}",
    )
    text = response.get("text")
    if not isinstance(text, str):
        raise ReceiptIntelligenceError("Receipt intelligence returned invalid OCR text")
    return text
