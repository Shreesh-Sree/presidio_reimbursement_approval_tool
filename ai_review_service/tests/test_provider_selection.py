from __future__ import annotations

from ai_review_service.config import AIReviewSettings
from ai_review_service.providers import GeminiNarrativeProvider, GroqNarrativeProvider
from ai_review_service.service import build_narrative_provider


def test_provider_selector_defaults_to_rule_based_without_a_vendor_client():
    assert build_narrative_provider(AIReviewSettings(environment="test")) is None
    assert build_narrative_provider(AIReviewSettings(environment="test", provider="groq")) is None


def test_provider_selector_uses_only_the_explicitly_selected_vendor():
    gemini = build_narrative_provider(
        AIReviewSettings(environment="test", provider="gemini", gemini_api_key="test-gemini-key", groq_api_key="ignored")
    )
    groq = build_narrative_provider(
        AIReviewSettings(environment="test", provider="groq", groq_api_key="test-groq-key", gemini_api_key="ignored")
    )

    assert isinstance(gemini, GeminiNarrativeProvider)
    assert isinstance(groq, GroqNarrativeProvider)
