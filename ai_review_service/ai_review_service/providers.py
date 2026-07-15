"""Narrative-provider abstraction with bounded retries and safe fallback."""

from __future__ import annotations

import asyncio
from collections import Counter
from collections.abc import Awaitable, Callable
import json
from typing import Protocol
from uuid import UUID

from .contracts import (
    FindingSeverity,
    NarrativeDraft,
    ProviderOutcome,
    ProviderReviewContext,
    ProviderStatus,
    ReviewRecommendation,
)
from .redaction import provider_prompt, redact_narrative


class NarrativeProvider(Protocol):
    """Optional generative provider; implementations receive minimized context."""

    name: str

    async def generate(self, context: ProviderReviewContext) -> NarrativeDraft: ...


def _parse_provider_payload(raw: str) -> dict[str, object]:
    """Parse the strictly JSON response, accepting an otherwise-empty fence.

    Some providers wrap valid JSON in a Markdown code fence despite an explicit
    JSON-only instruction.  Accept that harmless transport wrapper, but reject
    prose or non-object output so the resilient provider can safely fall back.
    """

    candidate = raw.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if len(lines) < 3 or lines[-1].strip() != "```":
            raise RuntimeError("Gemini did not return a structured advisory response")
        candidate = "\n".join(lines[1:-1]).strip()
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Gemini did not return a structured advisory response") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Gemini returned an invalid advisory response")
    return payload


class RuleBasedNarrativeProvider:
    """Deterministic provider used locally and whenever an LLM is unavailable."""

    name = "rule_based"

    async def generate(self, context: ProviderReviewContext) -> NarrativeDraft:
        findings = context.findings
        cited_finding_ids = tuple(finding.id for finding in findings)
        cited_policy_rule_refs = tuple(
            sorted({finding.policy_rule_ref for finding in findings if finding.policy_rule_ref})
        )
        if not findings:
            return NarrativeDraft(
                summary=(
                    f"The report contains {context.line_item_count} line item(s) totaling "
                    f"{context.report_total} {context.currency}. No deterministic policy or anomaly findings were detected."
                ),
                key_insights=("No policy-cap, receipt, duplicate, or historical-spend signal was triggered.",),
                recommendation=ReviewRecommendation.APPROVE,
                finding_ids=cited_finding_ids,
                policy_rule_refs=cited_policy_rule_refs,
            )

        severity_counts = Counter(finding.severity for finding in findings)
        finding_types = Counter(finding.finding_type.value.replace("_", " ") for finding in findings)
        high = severity_counts[FindingSeverity.HIGH]
        medium = severity_counts[FindingSeverity.MEDIUM]
        summary = (
            f"The report contains {context.line_item_count} line item(s) totaling "
            f"{context.report_total} {context.currency} and triggered {len(findings)} finding(s): "
            f"{high} high severity and {medium} medium severity."
        )
        insights = tuple(
            f"{count} {finding_type} finding(s)." for finding_type, count in finding_types.most_common(5)
        )
        return NarrativeDraft(
            summary=summary,
            key_insights=insights,
            recommendation=self.recommendation_for(context),
            finding_ids=cited_finding_ids,
            policy_rule_refs=cited_policy_rule_refs,
        )

    @staticmethod
    def recommendation_for(context: ProviderReviewContext) -> ReviewRecommendation:
        if context.risk_level in {FindingSeverity.HIGH, FindingSeverity.MEDIUM}:
            return ReviewRecommendation.REQUEST_INFORMATION
        return ReviewRecommendation.APPROVE


class GeminiNarrativeProvider:
    """Optional Gemini adapter.  The SDK is imported only when used."""

    name = "gemini"

    def __init__(self, *, api_key: str, model: str = "gemini-2.5-flash") -> None:
        if not api_key:
            raise ValueError("GeminiNarrativeProvider requires an API key")
        self._api_key = api_key
        self._model = model

    async def generate(self, context: ProviderReviewContext) -> NarrativeDraft:
        prompt = provider_prompt(context)

        def request() -> str:
            try:
                from google import genai
            except ImportError as exc:  # pragma: no cover - depends on optional install
                raise RuntimeError("Gemini support is not installed") from exc

            client = genai.Client(api_key=self._api_key)
            response = client.models.generate_content(model=self._model, contents=prompt)
            text = getattr(response, "text", None)
            if not text or not str(text).strip():
                raise RuntimeError("Gemini returned an empty response")
            return str(text).strip()

        raw = await asyncio.to_thread(request)
        # The model may improve prose and choose citations, but recommendation
        # remains deterministic and advisory-only.
        payload = _parse_provider_payload(raw)
        payload["recommendation"] = RuleBasedNarrativeProvider.recommendation_for(context)
        return NarrativeDraft.model_validate(payload)


Sleep = Callable[[float], Awaitable[None]]


def _validate_citations(draft: NarrativeDraft, context: ProviderReviewContext) -> NarrativeDraft:
    """Reject generated citations that are not grounded in the supplied facts."""

    allowed_finding_ids: set[UUID] = {finding.id for finding in context.findings}
    allowed_policy_rules = {finding.policy_rule_ref for finding in context.findings if finding.policy_rule_ref}
    if not set(draft.finding_ids).issubset(allowed_finding_ids):
        raise ValueError("provider cited a finding outside the supplied context")
    if not set(draft.policy_rule_refs).issubset(allowed_policy_rules):
        raise ValueError("provider cited a policy rule outside the supplied context")
    return draft


class ResilientNarrativeProvider:
    """Invoke an optional provider with timeout/retry, then fall back safely."""

    def __init__(
        self,
        primary: NarrativeProvider | None,
        *,
        fallback: NarrativeProvider | None = None,
        timeout_seconds: float = 8.0,
        max_attempts: int = 2,
        retry_backoff_seconds: float = 0.25,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least one")
        self._primary = primary
        self._fallback = fallback or RuleBasedNarrativeProvider()
        self._timeout_seconds = timeout_seconds
        self._max_attempts = max_attempts
        self._retry_backoff_seconds = retry_backoff_seconds
        self._sleep = sleep

    async def generate(self, context: ProviderReviewContext) -> ProviderOutcome:
        if self._primary is None or self._primary.name == self._fallback.name:
            draft = _validate_citations(redact_narrative(await self._fallback.generate(context)), context)
            return ProviderOutcome(
                provider_name=self._fallback.name,
                status=ProviderStatus.RULE_BASED,
                attempts=0,
                narrative=draft,
            )

        errors: list[str] = []
        for attempt in range(1, self._max_attempts + 1):
            try:
                draft = await asyncio.wait_for(
                    self._primary.generate(context), timeout=self._timeout_seconds
                )
                safe_draft = _validate_citations(redact_narrative(draft), context)
                return ProviderOutcome(
                    provider_name=self._primary.name,
                    status=ProviderStatus.GENERATED,
                    attempts=attempt,
                    narrative=safe_draft,
                )
            except TimeoutError:
                errors.append("timed out")
            except Exception as exc:  # provider failures must never expose secrets or raw response bodies
                errors.append(type(exc).__name__)

            if attempt < self._max_attempts and self._retry_backoff_seconds:
                await self._sleep(self._retry_backoff_seconds * attempt)

        draft = _validate_citations(redact_narrative(await self._fallback.generate(context)), context)
        return ProviderOutcome(
            provider_name=self._fallback.name,
            status=ProviderStatus.FALLBACK,
            attempts=self._max_attempts,
            used_fallback=True,
            failure_reason=f"{self._primary.name} unavailable ({', '.join(errors)})",
            narrative=draft,
        )
