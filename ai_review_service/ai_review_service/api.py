"""Private HTTP surface for the isolated AI review worker/service."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import secrets
from uuid import UUID

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import AIReviewSettings
from .contracts import (
    ExpenseReviewRequested,
    ReviewDisposition,
    ReviewDispositionRequest,
    ReviewJob,
)
from .service import ExpenseReviewService, build_service
from .worker import LocalReviewWorker


def _bearer_guard(service_token: str | None):
    """Build optional service-to-service bearer authentication.

    Local development can omit ``AI_REVIEW_SERVICE_TOKEN``.  Any configured
    value turns authentication on for every API operation, including the
    manual processing and disposition endpoints.
    """

    bearer = HTTPBearer(auto_error=False)

    async def require_service_token(
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    ) -> None:
        # Liveness endpoints reveal no review data and must remain probeable
        # when bearer authentication is enabled on the advisory API.
        if request.url.path in {"/health", "/ready"}:
            return
        if service_token is None:
            return
        if credentials is None or not secrets.compare_digest(credentials.credentials, service_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Valid AI review service credentials are required",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return require_service_token


def create_app(
    service: ExpenseReviewService | None = None,
    *,
    settings: AIReviewSettings | None = None,
) -> FastAPI:
    """Create an internal-only API; it is not mounted in the core FastAPI app."""

    settings = settings or AIReviewSettings()
    review_service = service or build_service(settings)
    worker = LocalReviewWorker(
        review_service,
        max_concurrency=settings.local_worker_max_concurrency,
        retry_delay_seconds=settings.local_worker_retry_delay_seconds,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        recovery_tasks: list[asyncio.Task[None]] = []
        if settings.auto_process_jobs:
            recovery_tasks = [
                asyncio.create_task(worker.process(job.id))
                for job in review_service.recover_pending_jobs()
            ]
        try:
            yield
        finally:
            for task in recovery_tasks:
                if not task.done():
                    task.cancel()
            if recovery_tasks:
                await asyncio.gather(*recovery_tasks, return_exceptions=True)

    app = FastAPI(
        title="Presidio AI Expense Review",
        version="1.0",
        description=(
            "Advisory-only review worker. Deploy behind an internal authenticated event gateway; "
            "it never approves, rejects, or updates reimbursement records."
        ),
        dependencies=[Depends(_bearer_guard(settings.service_token))],
        lifespan=lifespan,
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "ai-review"}

    @app.get("/ready")
    async def ready() -> dict[str, str]:
        return {"status": "ready", "service": "ai-review"}

    @app.post("/v1/review-jobs", response_model=ReviewJob, status_code=status.HTTP_202_ACCEPTED)
    async def enqueue_review(
        event: ExpenseReviewRequested, background_tasks: BackgroundTasks
    ) -> ReviewJob:
        job = review_service.enqueue(event)
        if settings.auto_process_jobs:
            background_tasks.add_task(worker.process, job.id)
        return job

    @app.get("/v1/review-jobs/{job_id}", response_model=ReviewJob)
    async def get_review_job(job_id: UUID) -> ReviewJob:
        job = review_service.get_job(job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review job not found")
        return job

    @app.post("/v1/review-jobs/{job_id}/process", response_model=ReviewJob)
    async def process_review_job(job_id: UUID) -> ReviewJob:
        try:
            return await review_service.process(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review job not found") from exc

    @app.post(
        "/v1/review-jobs/{job_id}/dispositions",
        response_model=ReviewDisposition,
        status_code=status.HTTP_201_CREATED,
    )
    async def record_human_disposition(
        job_id: UUID, request: ReviewDispositionRequest
    ) -> ReviewDisposition:
        try:
            return review_service.record_disposition(job_id, request)
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review job not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    @app.get("/v1/review-jobs/{job_id}/dispositions", response_model=tuple[ReviewDisposition, ...])
    async def list_human_dispositions(job_id: UUID) -> tuple[ReviewDisposition, ...]:
        if not review_service.get_job(job_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review job not found")
        return review_service.list_dispositions(job_id)

    return app
