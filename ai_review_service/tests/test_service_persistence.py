from ai_review_service.contracts import HumanDispositionAction, ReviewDispositionRequest, ReviewJobStatus
import pytest

from ai_review_service.persistence import SqliteReviewRepository
from ai_review_service.providers import ResilientNarrativeProvider
from ai_review_service.service import ExpenseReviewService


async def test_service_is_idempotent_persists_separately_and_records_human_verdict(tmp_path, event_factory):
    database_path = tmp_path / "ai-review.sqlite3"
    repository = SqliteReviewRepository(database_path)
    service = ExpenseReviewService(
        repository,
        narrative_provider=ResilientNarrativeProvider(None),
    )
    source_event = event_factory(
        items=(
            event_factory().items[0].model_copy(
                update={"description_excerpt": "Email alice@example.com about this expense"}
            ),
        )
    )

    first = service.enqueue(source_event)
    duplicate = service.enqueue(source_event)
    completed = await service.process(first.id)

    assert first.id == duplicate.id
    assert completed.status == ReviewJobStatus.COMPLETED
    assert completed.result is not None
    assert completed.result.human_review.required is True
    assert completed.result.human_review.automated_action_taken is False

    disposition = service.record_disposition(
        completed.id,
        ReviewDispositionRequest(
            reviewer_ref="manager:42",
            action=HumanDispositionAction.ACKNOWLEDGE,
            remarks="Asked alice@example.com for clarification",
        ),
    )
    assert "alice@example.com" not in (disposition.remarks or "")

    repository.close()
    reopened = SqliteReviewRepository(database_path)
    persisted = reopened.get_job(completed.id)
    assert persisted is not None
    assert "alice@example.com" not in (persisted.event.items[0].description_excerpt or "")
    assert reopened.list_dispositions(completed.id)[0].action == HumanDispositionAction.ACKNOWLEDGE
    reopened.close()


def test_ai_repository_refuses_the_core_postgres_connection_string():
    with pytest.raises(ValueError, match="core database"):
        SqliteReviewRepository("postgresql://reimbursement:password@localhost/reimbursement")


def test_recovery_requeues_interrupted_jobs_without_touching_core_data(tmp_path, event_factory):
    repository = SqliteReviewRepository(tmp_path / "ai-review.sqlite3")
    service = ExpenseReviewService(repository)
    queued = service.enqueue(event_factory())
    claimed = repository.claim(queued.id)
    assert claimed is not None
    assert claimed.status == ReviewJobStatus.PROCESSING

    recovered = service.recover_pending_jobs()

    assert [job.id for job in recovered] == [queued.id]
    assert recovered[0].status == ReviewJobStatus.RETRY_PENDING
    assert recovered[0].failure_reason == "review worker interrupted before completion"
    repository.close()
