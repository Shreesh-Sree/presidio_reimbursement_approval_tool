"""Untrusted document/query handling for direct and indirect prompt injection."""

from __future__ import annotations

from dataclasses import dataclass
import re


_INJECTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "instruction_override",
        re.compile(
            r"\b(?:ignore|disregard|override|forget|bypass)\b.{0,90}"
            r"\b(?:previous|prior|system|developer|assistant|instructions?|rules?|guardrails?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "role_prompt_reference",
        re.compile(
            r"\b(?:system|developer|assistant|tool)\s*(?:prompt|message|instructions?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "prompt_markup",
        re.compile(r"<\s*/?\s*(?:system|developer|assistant|tool)[^>]*>", re.IGNORECASE),
    ),
    (
        "jailbreak_or_exfiltration",
        re.compile(
            r"\b(?:jailbreak|prompt\s+injection|reveal\s+(?:the\s+)?(?:system|developer)"
            r"\s+prompt|exfiltrat(?:e|ion))\b",
            re.IGNORECASE,
        ),
    ),
    (
        "role_reassignment",
        re.compile(r"\b(?:you\s+are\s+now|act\s+as|new\s+instructions?)\b", re.IGNORECASE),
    ),
)

_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d .()\-]{6,}\d)(?!\w)")


@dataclass(frozen=True)
class SanitizationResult:
    text: str
    flags: tuple[str, ...]


def injection_flags(text: str) -> tuple[str, ...]:
    """Return deterministic labels without retaining or logging suspicious text."""

    return tuple(name for name, pattern in _INJECTION_PATTERNS if pattern.search(text))


def _normalise_whitespace(text: str) -> str:
    paragraphs = []
    for paragraph in text.splitlines():
        compact = " ".join(paragraph.split())
        if compact:
            paragraphs.append(compact)
    return "\n".join(paragraphs).strip()


def sanitize_policy_document(content: str) -> SanitizationResult:
    """Strip instruction-like lines before persistence and redact obvious contact PII.

    Indexed material is always treated as *data*.  Removing suspicious lines is
    conservative: it may omit some useful material, but it prevents a document
    from changing assistant behavior after retrieval.
    """

    flags: list[str] = []
    retained_lines: list[str] = []
    for line in content.splitlines() or [content]:
        line_flags = injection_flags(line)
        if line_flags:
            flags.extend(line_flags)
            continue
        retained_lines.append(line)

    sanitized = _normalise_whitespace("\n".join(retained_lines))
    redacted = _EMAIL.sub("[redacted-email]", sanitized)
    redacted = _PHONE.sub("[redacted-phone]", redacted)
    if redacted != sanitized:
        flags.append("contact_pii_redacted")
    return SanitizationResult(text=redacted, flags=tuple(sorted(set(flags))))


def validate_question(question: str) -> SanitizationResult:
    """Reject direct prompt injection instead of attempting to reinterpret it."""

    flags = injection_flags(question)
    if flags:
        return SanitizationResult(text="", flags=flags)
    return SanitizationResult(text=_normalise_whitespace(question), flags=())


def chunk_text(text: str, *, chunk_size: int, overlap: int) -> tuple[str, ...]:
    """Chunk deterministically, favoring sentence/word boundaries where possible."""

    if not text:
        return ()

    chunks: list[str] = []
    start = 0
    text_length = len(text)
    while start < text_length:
        nominal_end = min(text_length, start + chunk_size)
        end = nominal_end
        if nominal_end < text_length:
            window_start = start + (chunk_size // 2)
            candidate = max(
                text.rfind(". ", window_start, nominal_end),
                text.rfind("; ", window_start, nominal_end),
                text.rfind("\n", window_start, nominal_end),
                text.rfind(" ", window_start, nominal_end),
            )
            if candidate > start:
                end = candidate + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= text_length:
            break
        next_start = max(end - overlap, start + 1)
        start = next_start
    return tuple(chunks)


def safe_excerpt(text: str, *, max_chars: int = 480) -> str:
    """Return a citation-compatible excerpt from already sanitized policy data."""

    compact = " ".join(text.split())
    if len(compact) <= max_chars:
        return compact
    boundary = compact.rfind(" ", 0, max_chars)
    return f"{compact[: boundary if boundary > 0 else max_chars].rstrip()}…"
