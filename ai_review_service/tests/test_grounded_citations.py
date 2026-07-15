"""Generated narratives must cite only deterministic review facts."""

from __future__ import annotations

import pytest
from uuid import uuid4

from ai_review_service.contracts import NarrativeDraft, ReviewRecommendation
from ai_review_service.providers import ResilientNarrativeProvider
from ai_review_service.redaction import provider_context
from ai_review_service.rules import RuleEvaluator


class UngroundedCitationProvider:
    name = "ungrounded"

    async def generate(self, context):
        return NarrativeDraft(
            summary="This cites an unknown finding.",
            recommendation=ReviewRecommendation.APPROVE,
            finding_ids=(uuid4(),),
            policy_rule_refs=("policy:invented",),
        )


@pytest.mark.asyncio
async def test_ungrounded_generated_citations_fall_back_to_rule_based_output(event_factory):
    event = event_factory()
    context = provider_context(RuleEvaluator().evaluate(event), item_count=len(event.items))
    provider = ResilientNarrativeProvider(
        UngroundedCitationProvider(),
        timeout_seconds=1,
        max_attempts=1,
        retry_backoff_seconds=0,
    )

    outcome = await provider.generate(context)

    assert outcome.used_fallback is True
    assert outcome.provider_name == "rule_based"
    assert set(outcome.narrative.finding_ids) == {finding.id for finding in context.findings}
    assert set(outcome.narrative.policy_rule_refs).issubset(
        {finding.policy_rule_ref for finding in context.findings if finding.policy_rule_ref}
    )
