"""Core-to-RAG boundary stays optional, scoped, and free of user identity."""

from __future__ import annotations

from app.services import policy_assistant_client


def test_policy_index_event_uses_opaque_scope_references(monkeypatch, seeded_org, seeded_policy):
    captured: dict[str, object] = {}

    def fake_request(method, path, payload=None):
        captured.update({"method": method, "path": path, "payload": payload})
        return {
            "tenant_ref": payload["tenant_ref"],
            "policy_version_ref": payload["policy_version_ref"],
            "document_ref": payload["document_ref"],
            "document_digest": "a" * 64,
            "chunk_count": 1,
            "injection_flags": [],
        }

    monkeypatch.setenv("POLICY_ASSISTANT_SERVICE_URL", "http://policy-assistant.internal")
    monkeypatch.setenv("POLICY_ASSISTANT_REFERENCE_HMAC_KEY", "test-policy-reference-key")
    monkeypatch.setattr(policy_assistant_client, "_request", fake_request)

    result = policy_assistant_client.index_policy_text(
        organization_id=seeded_org.id,
        policy_id=seeded_policy.id,
        content="Airfare is reimbursable up to USD 500 per trip.",
    )

    payload = captured["payload"]
    assert captured["method"] == "POST"
    assert captured["path"] == "/v1/policy-documents"
    assert isinstance(payload, dict)
    assert payload["tenant_ref"].startswith("tenant-")
    assert payload["policy_version_ref"].startswith("policy-")
    assert payload["document_ref"].startswith("document-")
    assert seeded_org.name not in str(payload)
    for raw_identifier in (
        str(seeded_org.id),
        seeded_org.id.hex,
        str(seeded_policy.id),
        seeded_policy.id.hex,
    ):
        assert raw_identifier not in str(payload)
    assert result["chunk_count"] == 1


def test_policy_question_returns_only_the_service_grounded_payload(monkeypatch, seeded_org, seeded_policy):
    captured: dict[str, object] = {}

    def fake_request(method, path, payload=None):
        assert method == "POST"
        assert path == "/v1/ask"
        assert payload["question"] == "What is the airfare cap?"
        captured["payload"] = payload
        return {
            "answer": "Relevant indexed policy evidence: airfare is capped.",
            "evidence_found": True,
            "citations": [{"source_chunk_id": "chunk-123", "excerpt": "Airfare cap is USD 500."}],
        }

    monkeypatch.setenv("POLICY_ASSISTANT_SERVICE_URL", "http://policy-assistant.internal")
    monkeypatch.setenv("POLICY_ASSISTANT_REFERENCE_HMAC_KEY", "test-policy-reference-key")
    monkeypatch.setattr(policy_assistant_client, "_request", fake_request)

    result = policy_assistant_client.ask_policy(
        organization_id=seeded_org.id,
        policy_id=seeded_policy.id,
        question="What is the airfare cap?",
    )

    assert result["evidence_found"] is True
    assert result["citations"][0]["source_chunk_id"] == "chunk-123"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["tenant_ref"] == policy_assistant_client._scope(seeded_org.id, seeded_policy.id)[0]
    assert payload["policy_version_ref"] == policy_assistant_client._scope(seeded_org.id, seeded_policy.id)[1]
    assert str(seeded_org.id) not in str(payload)
    assert str(seeded_policy.id) not in str(payload)


def test_policy_scope_is_stable_for_the_same_key(monkeypatch, seeded_org, seeded_policy):
    monkeypatch.setenv("POLICY_ASSISTANT_REFERENCE_HMAC_KEY", "test-policy-reference-key")

    first = policy_assistant_client._scope(seeded_org.id, seeded_policy.id)
    second = policy_assistant_client._scope(seeded_org.id, seeded_policy.id)
    monkeypatch.setenv("POLICY_ASSISTANT_REFERENCE_HMAC_KEY", "rotated-policy-reference-key")
    after_key_rotation = policy_assistant_client._scope(seeded_org.id, seeded_policy.id)

    assert first == second
    assert first != after_key_rotation
    assert first[0] != policy_assistant_client._scope(seeded_policy.id, seeded_policy.id)[0]
