"""Private HTTP surface for the isolated AI review worker/service."""

from __future__ import annotations

from uuid import UUID

from fastapi import FastAPI, HTTPException, status

from .contracts import (
    ExpenseReviewRequested,
    ReviewDisposition,
    ReviewDispositionRequest,
    ReviewJob,
)
from .service import ExpenseReviewService, build_service


def create_app(service: ExpenseReviewService | None = None) -> FastAPI:
    """Create an internal-only API; it is not mounted in the core FastAPI app."""

    review_service = service or build_service()
    app = FastAPI(
        title="Presidio AI Expense Review",
        version="1.0",
        description=(
            "Advisory-only review worker. Deploy behind an internal authenticated event gateway; "
            "it never approves, rejects, or updates reimbursement records."
        ),
    )

    @app.post("/v1/review-jobs", response_model=ReviewJob, status_code=status.HTTP_202_ACCEPTED)
    async def enqueue_review(event: ExpenseReviewRequested) -> ReviewJob:
        return review_service.enqueue(event)

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
