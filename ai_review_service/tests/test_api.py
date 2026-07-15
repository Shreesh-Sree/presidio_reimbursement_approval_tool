from fastapi.testclient import TestClient

from ai_review_service.api import create_app
from ai_review_service.persistence import InMemoryReviewRepository
from ai_review_service.service import ExpenseReviewService


def test_private_ai_service_exposes_advisory_job_contract(event_factory):
    service = ExpenseReviewService(InMemoryReviewRepository())
    client = TestClient(create_app(service))
    event = event_factory()

    queued = client.post("/v1/review-jobs", json=event.model_dump(mode="json"))
    assert queued.status_code == 202
    job_id = queued.json()["id"]

    completed = client.post(f"/v1/review-jobs/{job_id}/process")
    assert completed.status_code == 200
    payload = completed.json()
    assert payload["status"] == "completed"
    assert payload["result"]["human_review"]["required"] is True
    assert payload["result"]["human_review"]["automated_action_taken"] is False
