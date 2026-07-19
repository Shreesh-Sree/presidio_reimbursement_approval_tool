from fastapi.testclient import TestClient

from ai_review_service.api import create_app
from ai_review_service.config import AIReviewSettings
from ai_review_service.contracts import HumanDispositionAction, ReviewDispositionRequest
from ai_review_service.persistence import InMemoryReviewRepository
from ai_review_service.service import ExpenseReviewService


def test_private_ai_service_exposes_advisory_job_contract(event_factory):
    service = ExpenseReviewService(InMemoryReviewRepository())
    client = TestClient(
        create_app(
            service,
            settings=AIReviewSettings(environment="test", service_token=None, auto_process_jobs=True),
        )
    )
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


def test_new_jobs_are_processed_automatically_by_the_local_worker(event_factory):
    service = ExpenseReviewService(InMemoryReviewRepository())
    client = TestClient(
        create_app(
            service,
            settings=AIReviewSettings(
                environment="test",
                service_token=None,
                auto_process_jobs=True,
                local_worker_retry_delay_seconds=0,
            ),
        )
    )

    response = client.post("/v1/review-jobs", json=event_factory().model_dump(mode="json"))

    assert response.status_code == 202
    completed = client.get(f"/v1/review-jobs/{response.json()['id']}")
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert completed.json()["result"]["human_review"]["required"] is True


def test_configured_service_token_protects_every_review_endpoint(event_factory):
    token = "ai-review-test-token"
    service = ExpenseReviewService(InMemoryReviewRepository())
    client = TestClient(
        create_app(
            service,
            settings=AIReviewSettings(environment="test", service_token=token, auto_process_jobs=False),
        )
    )
    event = event_factory()

    denied_enqueue = client.post("/v1/review-jobs", json=event.model_dump(mode="json"))
    assert denied_enqueue.status_code == 401
    assert denied_enqueue.headers["www-authenticate"] == "Bearer"
    assert (
        client.post(
            "/v1/review-jobs",
            json=event.model_dump(mode="json"),
            headers={"Authorization": "Bearer incorrect-token"},
        ).status_code
        == 401
    )

    headers = {"Authorization": f"Bearer {token}"}
    queued = client.post("/v1/review-jobs", json=event.model_dump(mode="json"), headers=headers)
    assert queued.status_code == 202
    job_id = queued.json()["id"]

    denied_requests = (
        client.get(f"/v1/review-jobs/{job_id}"),
        client.post(f"/v1/review-jobs/{job_id}/process"),
        client.get(f"/v1/review-jobs/{job_id}/dispositions"),
        client.post(
            f"/v1/review-jobs/{job_id}/dispositions",
            json=ReviewDispositionRequest(
                reviewer_ref="manager:42",
                action=HumanDispositionAction.ACKNOWLEDGE,
            ).model_dump(mode="json"),
        ),
    )
    assert all(response.status_code == 401 for response in denied_requests)

    assert client.post(f"/v1/review-jobs/{job_id}/process", headers=headers).status_code == 200
