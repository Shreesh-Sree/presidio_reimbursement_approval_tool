from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.routes import policies
from app.core.database import get_db
from app.models.policy import Policy
from app.services import policy_assistant_client


def _client_for_policy_assistant(engine, seeded_user):
    app = FastAPI()
    app.include_router(policies.router)

    def override_db():
        session = Session(engine)
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    for route in policies.router.routes:
        for dependency in route.dependant.dependencies:
            if dependency.call is not get_db:
                app.dependency_overrides[dependency.call] = lambda: {
                    "user_id": str(seeded_user.id),
                    "email": seeded_user.email,
                    "organization_id": str(seeded_user.organization_id),
                }
    return TestClient(app)


def test_policy_assistant_indexes_admin_text_and_returns_grounded_answer(engine, db, seeded_user, monkeypatch):
    policy = Policy(
        organization_id=seeded_user.organization_id,
        name="Travel policy",
        version_label="v1",
        effective_from=datetime.now(UTC),
    )
    db.add(policy)
    db.commit()

    indexed: dict[str, object] = {}
    asked: dict[str, object] = {}

    def fake_index(**kwargs):
        indexed.update(kwargs)
        return {"document_ref": "document-safe", "chunk_count": 2}

    def fake_ask(**kwargs):
        asked.update(kwargs)
        return {
            "answer": "Airfare is capped at $500 per trip.",
            "citations": [{"document_ref": "document-safe", "chunk_index": 0}],
            "grounded": True,
        }

    monkeypatch.setattr(policy_assistant_client, "index_policy_text", fake_index)
    monkeypatch.setattr(policy_assistant_client, "ask_policy", fake_ask)

    with _client_for_policy_assistant(engine, seeded_user) as client:
        indexed_response = client.post(
            f"/api/policies/{policy.id}/assistant-index",
            json={"content": "Travel policy: airfare is capped at $500 per trip."},
        )
        assert indexed_response.status_code == 200, indexed_response.text
        assert indexed_response.json() == {
            "policy_id": str(policy.id),
            "indexing": {"document_ref": "document-safe", "chunk_count": 2},
        }

        answer_response = client.post(
            f"/api/policies/{policy.id}/assistant-ask",
            json={"question": "What is the airfare cap?", "top_k": 2},
        )
        assert answer_response.status_code == 200, answer_response.text
        body = answer_response.json()
        assert body["answer"]["grounded"] is True
        assert body["answer"]["citations"][0]["document_ref"] == "document-safe"

    assert indexed == {
        "organization_id": str(seeded_user.organization_id),
        "policy_id": str(policy.id),
        "content": "Travel policy: airfare is capped at $500 per trip.",
    }
    assert asked == {
        "organization_id": str(seeded_user.organization_id),
        "policy_id": str(policy.id),
        "question": "What is the airfare cap?",
        "top_k": 2,
    }


def test_policy_assistant_reports_safe_unavailable_error(engine, db, seeded_user, monkeypatch):
    policy = Policy(
        organization_id=seeded_user.organization_id,
        name="Meals policy",
        version_label="v1",
        effective_from=datetime.now(UTC),
    )
    db.add(policy)
    db.commit()
    monkeypatch.setattr(
        policy_assistant_client,
        "ask_policy",
        lambda **_kwargs: (_ for _ in ()).throw(policy_assistant_client.PolicyAssistantError("Policy assistant is unavailable")),
    )

    with _client_for_policy_assistant(engine, seeded_user) as client:
        response = client.post(
            f"/api/policies/{policy.id}/assistant-ask",
            json={"question": "What is the meal cap?"},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "Policy assistant is unavailable"
