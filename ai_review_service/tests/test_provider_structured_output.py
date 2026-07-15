from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from ai_review_service.contracts import ExpenseLineSnapshot, ReceiptEvidence, ReviewRecommendation
from ai_review_service.providers import GroqNarrativeProvider, _parse_provider_payload
from ai_review_service.redaction import provider_context
from ai_review_service.rules import RuleEvaluator


def test_structured_provider_payload_accepts_a_json_code_fence_without_prose():
    payload = _parse_provider_payload(
        """```json
        {"summary":"Policy evidence found.","key_insights":[],"finding_ids":[],"policy_rule_refs":[]}
        ```"""
    )

    assert payload == {
        "summary": "Policy evidence found.",
        "key_insights": [],
        "finding_ids": [],
        "policy_rule_refs": [],
    }


@pytest.mark.asyncio
async def test_groq_provider_requests_json_object_mode_and_parses_mocked_response(event_factory, monkeypatch):
    event = event_factory(
        items=(
            ExpenseLineSnapshot(
                line_id=uuid4(),
                expense_date=date(2026, 7, 1),
                category_code="travel",
                subcategory_code="airfare",
                vendor_code="airline_a",
                amount=Decimal("120.00"),
                currency="usd",
                receipt=ReceiptEvidence(attached=True, digest="a" * 64),
            ),
        )
    )
    context = provider_context(RuleEvaluator().evaluate(event), item_count=len(event.items))
    captured: dict[str, object] = {}
    finding = context.findings[0]

    class FakeGroq:
        def __init__(self, *, api_key: str) -> None:
            captured["api_key"] = api_key
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

        def create(self, **kwargs):
            captured["request"] = kwargs
            return SimpleNamespace(
                choices=(
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content=(
                                '{"summary":"Review the flagged evidence.",'
                                '"key_insights":["Policy finding requires review."],'
                                f'"finding_ids":["{finding.id}"],'
                                f'"policy_rule_refs":["{finding.policy_rule_ref}"]}}'
                            )
                        )
                    ),
                )
            )

    monkeypatch.setitem(sys.modules, "groq", SimpleNamespace(Groq=FakeGroq))

    draft = await GroqNarrativeProvider(api_key="test-key", model="test-model").generate(context)

    assert draft.summary == "Review the flagged evidence."
    assert draft.finding_ids == (finding.id,)
    assert draft.policy_rule_refs == (finding.policy_rule_ref,)
    assert draft.recommendation == ReviewRecommendation.REQUEST_INFORMATION
    assert captured["api_key"] == "test-key"
    request = captured["request"]
    assert isinstance(request, dict)
    assert request["model"] == "test-model"
    assert request["response_format"] == {"type": "json_object"}
    assert request["temperature"] == 0
    assert all("report_id" not in str(message) for message in request["messages"])
