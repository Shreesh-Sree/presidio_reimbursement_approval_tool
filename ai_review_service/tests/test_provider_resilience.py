import asyncio

import pytest

from ai_review_service.contracts import NarrativeDraft, ReviewRecommendation
from ai_review_service.providers import ResilientNarrativeProvider
from ai_review_service.redaction import provider_context
from ai_review_service.rules import RuleEvaluator


class FailingProvider:
    name = "test_provider"

    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, context):
        self.calls += 1
        raise RuntimeError("provider response contains a secret")


class SlowProvider:
    name = "slow_provider"

    async def generate(self, context):
        await asyncio.sleep(0.05)
        return NarrativeDraft(summary="late", recommendation=ReviewRecommendation.APPROVE)


@pytest.mark.asyncio
async def test_failed_provider_retries_then_returns_safe_rule_based_fallback(event_factory):
    event = event_factory()
    context = provider_context(RuleEvaluator().evaluate(event), item_count=len(event.items))
    failing = FailingProvider()
    provider = ResilientNarrativeProvider(
        failing,
        timeout_seconds=1,
        max_attempts=2,
        retry_backoff_seconds=0,
    )

    outcome = await provider.generate(context)

    assert failing.calls == 2
    assert outcome.used_fallback is True
    assert outcome.attempts == 2
    assert outcome.provider_name == "rule_based"
    assert "secret" not in (outcome.failure_reason or "")


@pytest.mark.asyncio
async def test_timed_out_provider_falls_back(event_factory):
    event = event_factory()
    context = provider_context(RuleEvaluator().evaluate(event), item_count=len(event.items))
    provider = ResilientNarrativeProvider(
        SlowProvider(),
        timeout_seconds=0.001,
        max_attempts=1,
        retry_backoff_seconds=0,
    )

    outcome = await provider.generate(context)

    assert outcome.used_fallback is True
    assert "timed out" in (outcome.failure_reason or "")
