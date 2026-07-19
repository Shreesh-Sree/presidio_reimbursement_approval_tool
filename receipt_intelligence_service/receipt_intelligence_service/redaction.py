"""Conservative text minimization before an external AI provider boundary."""

from __future__ import annotations

import re


_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d(). -]{7,}\d)(?!\w)")
_PAYMENT_NUMBER = re.compile(r"(?<!\d)(?:\d[ -]?){12,19}\d(?!\d)")
_CUSTOMER_FIELD = re.compile(
    r"(?im)^\s*(?:customer|customer\s*name|name|bill\s*to|ship\s*to|email|phone|address)\s*[:#-]\s*[^\n]+"
)
_ADDRESS_LINE = re.compile(
    r"(?im)^\s*\d{1,6}\s+[^\n]{1,80}\s+(?:street|st\.?|road|rd\.?|avenue|ave\.?|lane|ln\.?|drive|dr\.?|boulevard|blvd\.?)\b[^\n]*"
)
_LONG_IDENTIFIER = re.compile(r"\b[A-Z0-9][A-Z0-9-]{11,}\b", re.IGNORECASE)


def redact_for_external_provider(text: str, *, max_chars: int) -> str:
    """Return only receipt facts suitable for an approved external provider.

    Rule-based extraction still receives the local text.  This transform is
    deliberately lossy: a provider does not need customer contact data,
    payment numbers, street addresses, or long account/reference identifiers
    to suggest a merchant/date/amount.
    """

    bounded = text[:max_chars]
    redacted = _CUSTOMER_FIELD.sub("[REDACTED_FIELD]", bounded)
    redacted = _ADDRESS_LINE.sub("[REDACTED_ADDRESS]", redacted)
    redacted = _EMAIL.sub("[REDACTED_EMAIL]", redacted)
    redacted = _PHONE.sub("[REDACTED_PHONE]", redacted)
    redacted = _PAYMENT_NUMBER.sub("[REDACTED_PAYMENT]", redacted)
    return _LONG_IDENTIFIER.sub("[REDACTED_IDENTIFIER]", redacted)
