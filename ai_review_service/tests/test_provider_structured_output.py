from __future__ import annotations

from ai_review_service.providers import _parse_provider_payload


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
