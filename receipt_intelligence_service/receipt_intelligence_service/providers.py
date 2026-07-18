"""LLM-backed receipt evidence extraction with deterministic fallback."""

from __future__ import annotations

import asyncio
import json
import logging

from .config import ReceiptIntelligenceSettings
from .contracts import ReceiptEvidence
from .analysis import extract_evidence as rule_based_extract


logger = logging.getLogger("receipt_intelligence.provider")


class GroqReceiptProvider:
    """Extract receipt evidence via Groq LLM API."""

    def __init__(self, *, api_key: str, model: str, timeout_seconds: float) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds

    async def extract(self, text: str) -> ReceiptEvidence:
        try:
            from groq import AsyncGroq
        except ImportError as exc:
            raise RuntimeError("Groq SDK not installed — run: pip install groq") from exc

        client = AsyncGroq(api_key=self._api_key, timeout=self._timeout_seconds, max_retries=0)
        try:
            response = await client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a receipt data extraction assistant. "
                            "Extract structured data from receipt text. "
                            "Return ONLY a JSON object with these fields:\n"
                            '- "merchant_candidates": list of merchant/store names found (max 3)\n'
                            '- "date_candidates": list of dates found in any format (max 3)\n'
                            '- "amount_candidates": list of amounts with currency like "INR 1234.56" (max 3, prefer totals/grand totals)\n'
                            '- "masked_receipt_number_candidates": list of receipt/invoice numbers with first chars masked as "••••XXXX" (max 3)\n'
                            "If a field has no data, use an empty list. Do not invent data."
                        ),
                    },
                    {"role": "user", "content": text[:8000]},
                ],
                response_format={"type": "json_object"},
                temperature=0,
            )
            content = response.choices[0].message.content
            if not content or not content.strip():
                raise RuntimeError("Empty response from Groq")
            payload = json.loads(content.strip())
            return ReceiptEvidence(
                merchant_candidates=tuple(str(m)[:80] for m in (payload.get("merchant_candidates") or [])[:3]),
                date_candidates=tuple(str(d) for d in (payload.get("date_candidates") or [])[:3]),
                amount_candidates=tuple(str(a) for a in (payload.get("amount_candidates") or [])[:3]),
                masked_receipt_number_candidates=tuple(
                    str(r) for r in (payload.get("masked_receipt_number_candidates") or [])[:3]
                ),
            )
        finally:
            await client.close()


class ResilientReceiptProvider:
    """Try LLM extraction first, fall back to rule-based on failure."""

    def __init__(
        self,
        primary: GroqReceiptProvider | None,
        *,
        timeout_seconds: float = 8.0,
        max_attempts: int = 2,
    ) -> None:
        self._primary = primary
        self._timeout_seconds = timeout_seconds
        self._max_attempts = max_attempts

    async def extract(self, text: str) -> tuple[ReceiptEvidence, str]:
        """Returns (evidence, provider_name)."""
        if self._primary is None:
            return rule_based_extract(text), "rule_based"

        for attempt in range(1, self._max_attempts + 1):
            try:
                evidence = await asyncio.wait_for(
                    self._primary.extract(text), timeout=self._timeout_seconds
                )
                return evidence, "groq"
            except Exception as exc:
                logger.warning(
                    "groq_extraction_failed",
                    extra={"attempt": attempt, "error": type(exc).__name__},
                )

        return rule_based_extract(text), "rule_based_fallback"


def build_provider(settings: ReceiptIntelligenceSettings) -> ResilientReceiptProvider:
    """Build a resilient provider: Groq primary (if key set), rule-based fallback."""
    primary = None
    if settings.groq_api_key:
        primary = GroqReceiptProvider(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            timeout_seconds=settings.groq_timeout_seconds,
        )
    return ResilientReceiptProvider(
        primary,
        timeout_seconds=settings.groq_timeout_seconds,
        max_attempts=settings.groq_max_attempts,
    )
