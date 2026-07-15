"""Application service orchestrating isolated AI review jobs."""

from __future__ import annotations

from uuid import UUID

from .config import AIReviewSettings
from .contracts import (
    ExpenseReviewRequested,
    ReviewDisposition,
    ReviewDispositionRequest,
    ReviewJob,
    ReviewJobStatus,
    ReviewResult,
)
from .persistence import ReviewRepository, SqliteReviewRepository
from .providers import (
    GeminiNarrativeProvider,
    GroqNarrativeProvider,
    NarrativeProvider,
    ResilientNarrativeProvider,
    RuleBasedNarrativeProvider,
)
from .redaction import minimise_event, provider_context, redact_text
from .rules import RuleEvaluator


class ExpenseReviewService:
    """Run advisory reviews without importing or mutating core application state."""

    def __init__(
        self,
        repository: ReviewRepository,
        *,
        evaluator: RuleEvaluator | None = None,
        narrative_provider: ResilientNarrativeProvider | None = None,
        job_max_attempts: int = 3,
    ) -> None:
        self._repository = repository
        self._evaluator = evaluator or RuleEvaluator()
        self._narrative_provider = narrative_provider or ResilientNarrativeProvider(None)
        self._job_max_attempts = job_max_attempts

    def enqueue(self, event: ExpenseReviewRequested) -> ReviewJob:
        """Persist an idempotent, minimized job for asynchronous processing."""

        return self._repository.enqueue(minimise_event(event), max_attempts=self._job_max_attempts)

    def get_job(self, job_id: UUID) -> ReviewJob | None:
        return self._repository.get_job(job_id)

    def recover_pending_jobs(self) -> tuple[ReviewJob, ...]:
        """Return queued work after recovering an interrupted local worker."""

        return self._repository.recover_pending_jobs()

    async def process(self, job_id: UUID) -> ReviewJob:
        """Process one job; provider failure falls back to deterministic prose."""

        job = self._repository.claim(job_id)
        if not job:
            raise KeyError(f"review job {job_id} was not found")
        if job.status != ReviewJobStatus.PROCESSING:
            return job

        try:
            evaluation = self._evaluator.evaluate(job.event)
            context = provider_context(evaluation, item_count=len(job.event.items))
            outcome = await self._narrative_provider.generate(context)
            result = ReviewResult(
                job_id=job.id,
                event_id=job.event.event_id,
                report_id=job.event.report_id,
                evaluation=evaluation,
                summary=outcome.narrative.summary,
                key_insights=outcome.narrative.key_insights,
                recommendation=outcome.narrative.recommendation,
                cited_finding_ids=outcome.narrative.finding_ids,
                cited_policy_rule_refs=outcome.narrative.policy_rule_refs,
                provider=outcome,
            )
            return self._repository.complete(job.id, result)
        except Exception as exc:
            # Do not persist exception text: it can contain provider responses,
            # credentials, or upstream values.  The job retry state is enough for
            # an operator to diagnose from protected service logs.
            return self._repository.retry_or_fail(
                job.id, f"review processing failed ({type(exc).__name__})"
            )

    def record_disposition(
        self, job_id: UUID, request: ReviewDispositionRequest
    ) -> ReviewDisposition:
        """Append a human verdict without changing the core workflow itself."""

        safe_request = request.model_copy(update={"remarks": redact_text(request.remarks, limit=1_000)})
        return self._repository.record_disposition(job_id, safe_request)

    def list_dispositions(self, job_id: UUID) -> tuple[ReviewDisposition, ...]:
        return self._repository.list_dispositions(job_id)


def build_narrative_provider(settings: AIReviewSettings) -> NarrativeProvider | None:
    """Select one optional provider without falling through to another vendor.

    An unavailable selected provider deliberately returns ``None`` so the
    resilient wrapper uses the deterministic rule-based narrative. This keeps
    key rotation or a vendor outage from altering the advisory boundary.
    """

    if settings.provider == "gemini" and settings.gemini_api_key:
        return GeminiNarrativeProvider(api_key=settings.gemini_api_key, model=settings.gemini_model)
    if settings.provider == "groq" and settings.groq_api_key:
        return GroqNarrativeProvider(api_key=settings.groq_api_key, model=settings.groq_model)
    return None


def build_service(settings: AIReviewSettings | None = None) -> ExpenseReviewService:
    """Build the deployable service using its own persistence configuration."""

    settings = settings or AIReviewSettings()
    primary = build_narrative_provider(settings)
    provider = ResilientNarrativeProvider(
        primary,
        fallback=RuleBasedNarrativeProvider(),
        timeout_seconds=settings.provider_timeout_seconds,
        max_attempts=settings.provider_max_attempts,
        retry_backoff_seconds=settings.provider_retry_backoff_seconds,
    )
    return ExpenseReviewService(
        SqliteReviewRepository(settings.database_path),
        narrative_provider=provider,
        job_max_attempts=settings.job_max_attempts,
    )
