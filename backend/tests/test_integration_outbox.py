"""Lease and idempotency coverage for integration outbox dispatch."""

from __future__ import annotations

import uuid

from app.models.approval_history import ApprovalHistory
from app.models.integration_outbox import IntegrationOutbox
from app.services import ai_review_client, integration_outbox_service
from app.services.report_service import create_draft


def test_outbox_claim_is_conditional_and_not_repeated(db):
    row = IntegrationOutbox(
        event_type="ai_review.requested",
        aggregate_type="expense_report",
        aggregate_id=uuid.uuid4(),
        dedupe_key="test-ai-event-1",
        payload_json={"event_id": "event-1"},
        status="pending",
        attempt_count=0,
        available_at=integration_outbox_service.utcnow(),
    )
    db.add(row)
    db.commit()

    assert integration_outbox_service._claim(db, limit=10, worker="worker-one") == [row.id]
    assert integration_outbox_service._claim(db, limit=10, worker="worker-two") == []


def test_human_disposition_is_durable_and_uses_an_opaque_reviewer_ref(db, seeded_user, monkeypatch):
    report = create_draft(db, seeded_user.id, seeded_user.department_id, "AI disposition")
    report.status = "approved_pending_payment"
    report.ai_review_job_id = uuid.uuid4()
    db.add(
        ApprovalHistory(
            expense_report_id=report.id,
            action="approve",
            performed_by=seeded_user.id,
        )
    )
    db.flush()
    monkeypatch.setenv("AI_REVIEW_SERVICE_URL", "http://ai-review.internal")

    row = integration_outbox_service.enqueue_human_disposition(
        db,
        report,
        seeded_user.id,
        "approve",
        "Looks good",
    )
    assert row is not None
    assert str(seeded_user.id) not in str(row.payload_json)
    db.commit()

    captured: dict[str, object] = {}

    def fake_request(method, path, payload=None):
        if method == "GET":
            return {"status": "completed"}
        captured.update({"path": path, "payload": payload})
        return {}

    monkeypatch.setattr(ai_review_client, "_request", fake_request)
    assert integration_outbox_service.deliver_pending_ai_reviews(db) == 1
    db.refresh(row)
    assert row.status == "processed"
    assert isinstance(captured["payload"], dict)
    assert captured["payload"]["reviewer_ref"].startswith("subject-")
