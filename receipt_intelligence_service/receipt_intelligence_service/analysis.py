"""Deterministic in-memory analysis of caller-supplied receipt plain text."""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal, InvalidOperation
import re

from .contracts import ReceiptEvidence


_INSTRUCTION_PATTERNS = (
    re.compile(
        r"(?i)\b(?:ignore|disregard|override)\s+(?:all\s+)?(?:previous|prior|above|system|developer)"
        r"[^\n]{0,100}\b(?:instruction|prompt|rule)s?\b"
    ),
    re.compile(r"(?i)\b(?:system\s+prompt|developer\s+message|jailbreak|prompt\s+injection)\b"),
    re.compile(r"(?i)^\s*(?:assistant|system|developer)\s*:"),
    re.compile(r"(?i)\[\s*(?:inst|system|assistant|developer)\s*\]"),
)
_MERCHANT_PATTERN = re.compile(
    r"(?im)^\s*(?:merchant|vendor|store|sold\s+by)\s*(?:name)?\s*[:#-]\s*([^\n]{2,96})"
)
_DATE_PATTERN = re.compile(
    r"\b(?:20\d{2}[-/.](?:0[1-9]|1[0-2])[-/.](?:0[1-9]|[12]\d|3[01])"
    r"|(?:0?[1-9]|[12]\d|3[01])[-/.](?:0?[1-9]|1[0-2])[-/.]20\d{2}"
    r"|(?:0?[1-9]|[12]\d|3[01])\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
    r"\s+20\d{2})\b",
    re.IGNORECASE,
)
_AMOUNT_PATTERN = re.compile(
    r"(?im)\b(?:grand\s+total|total|amount|paid|subtotal)\s*[:=]?\s*"
    r"(?:(USD|EUR|GBP|INR)\s*)?([\$€£₹])?\s*"
    r"([0-9]{1,9}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)\b"
)
_RECEIPT_NUMBER_PATTERN = re.compile(
    r"(?im)\b(?:receipt|invoice|transaction|order)\s*"
    r"(?:number|no\.?|#|id)?\s*[:#-]?\s*([A-Z0-9][A-Z0-9-]{3,48})\b"
)
_EMAIL_PATTERN = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?\d[\d .()-]{7,}\d)(?!\d)")
_CURRENCY_SYMBOLS = {"$": "USD", "€": "EUR", "£": "GBP", "₹": "INR"}


def strip_suspicious_instructions(text: str) -> tuple[str, int]:
    """Remove lines that look like instructions before extracting evidence."""

    safe_lines: list[str] = []
    suspicious_line_count = 0
    for line in text.splitlines():
        if any(pattern.search(line) for pattern in _INSTRUCTION_PATTERNS):
            suspicious_line_count += 1
            continue
        safe_lines.append(line)
    return "\n".join(safe_lines), suspicious_line_count


def extract_evidence(text: str, *, max_candidates: int = 3) -> ReceiptEvidence:
    """Extract a bounded set of labels/amounts without retaining the source text."""

    merchants = _unique(
        (
            _safe_merchant(match.group(1))
            for match in _MERCHANT_PATTERN.finditer(text)
        ),
        max_candidates,
    )
    dates = _unique((match.group(0) for match in _DATE_PATTERN.finditer(text)), max_candidates)
    amounts = _unique(
        (
            _normalise_amount(match.group(3), match.group(1), match.group(2))
            for match in _AMOUNT_PATTERN.finditer(text)
        ),
        max_candidates,
    )
    receipt_numbers = _unique(
        (_mask_identifier(match.group(1)) for match in _RECEIPT_NUMBER_PATTERN.finditer(text)),
        max_candidates,
    )
    return ReceiptEvidence(
        merchant_candidates=tuple(item for item in merchants if item),
        date_candidates=dates,
        amount_candidates=tuple(item for item in amounts if item),
        masked_receipt_number_candidates=tuple(item for item in receipt_numbers if item),
    )


def _unique(values: Iterable[str | None], max_candidates: int) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value:
            continue
        candidate = str(value).strip()
        key = candidate.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(candidate)
        if len(result) >= max_candidates:
            break
    return tuple(result)


def _safe_merchant(value: str) -> str | None:
    cleaned = _PHONE_PATTERN.sub("[redacted]", _EMAIL_PATTERN.sub("[redacted]", value)).strip(" -:#")
    if not cleaned or any(pattern.search(cleaned) for pattern in _INSTRUCTION_PATTERNS):
        return None
    return cleaned[:80]


def _normalise_amount(value: str, code: str | None, symbol: str | None) -> str | None:
    try:
        amount = Decimal(value.replace(",", "")).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None
    currency = code or _CURRENCY_SYMBOLS.get(symbol or "")
    return f"{currency} {amount}" if currency else str(amount)


def _mask_identifier(value: str) -> str:
    compact = value.strip()
    suffix = compact[-4:] if len(compact) > 4 else compact
    return f"••••{suffix}"
