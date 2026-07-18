"""PostgreSQL review persistence for production deployments (Supabase)."""

from __future__ import annotations

import threading
from pathlib import Path
from uuid import UUID

from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row

from .contracts import (
    ExpenseReviewRequested,
    ReviewDisposition,
    ReviewDispositionRequest,
    ReviewJob,
    ReviewJobStatus,
    ReviewResult,
    utc_now,
)
from .persistence import ReviewRepository, _copy_job, InMemoryReviewRepository


class PostgresReviewRepository:
    """Supabase PostgreSQL-backed review job store using JSONB blobs."""

    def __init__(self, database_url: str) -> None:
        if not database_url:
            raise ValueError("database_url is required for PostgreSQL persistence")
        self._pool = ConnectionPool(database_url, min_size=1, max_size=4)
        self._lock = threading.RLock()
        self._create_schema()

    def close(self) -> None:
        self._pool.close()

    def ping(self) -> bool:
        with self._pool.connection() as conn:
            conn.execute("SELECT 1")
        return True

    def enqueue(self, event: ExpenseReviewRequested, *, max_attempts: int) -> ReviewJob:
        with self._lock:
            existing = self._job_for_event(event.event_id)
            if existing:
                return existing
            job = ReviewJob(event=event, max_attempts=max_attempts)
            with self._pool.connection() as conn:
                conn.execute(
                    "INSERT INTO ai_review_jobs (id, event_id, job_json) VALUES (%s, %s, %s)",
                    (str(job.id), str(event.event_id), job.model_dump_json()),
                )
                conn.commit()
            return _copy_job(job)

    def get_job(self, job_id: UUID) -> ReviewJob | None:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT job_json FROM ai_review_jobs WHERE id = %s", (str(job_id),)
            )
            row = cur.fetchone()
        return ReviewJob.model_validate_json(row[0]) if row else None

    def claim(self, job_id: UUID) -> ReviewJob | None:
        with self._lock:
            job = self.get_job(job_id)
            if not job:
                return None
            if job.status not in {ReviewJobStatus.QUEUED, ReviewJobStatus.RETRY_PENDING}:
                return job
            claimed = job.model_copy(
                update={
                    "status": ReviewJobStatus.PROCESSING,
                    "attempt_count": job.attempt_count + 1,
                    "updated_at": utc_now(),
                    "failure_reason": None,
                }
            )
            self._save_job(claimed)
            return claimed

    def complete(self, job_id: UUID, result: ReviewResult) -> ReviewJob:
        with self._lock:
            job = self._require_job(job_id)
            if job.status != ReviewJobStatus.PROCESSING:
                raise ValueError("only a processing job can be completed")
            if result.job_id != job_id:
                raise ValueError("result job ID does not match")
            completed = job.model_copy(
                update={
                    "status": ReviewJobStatus.COMPLETED,
                    "result": result,
                    "failure_reason": None,
                    "updated_at": utc_now(),
                }
            )
            self._save_job(completed)
            return completed

    def retry_or_fail(self, job_id: UUID, failure_reason: str) -> ReviewJob:
        with self._lock:
            job = self._require_job(job_id)
            if job.status != ReviewJobStatus.PROCESSING:
                raise ValueError("only a processing job can be retried or failed")
            status = (
                ReviewJobStatus.RETRY_PENDING
                if job.attempt_count < job.max_attempts
                else ReviewJobStatus.FAILED
            )
            updated = job.model_copy(
                update={"status": status, "failure_reason": failure_reason[:500], "updated_at": utc_now()}
            )
            self._save_job(updated)
            return updated

    def recover_pending_jobs(self) -> tuple[ReviewJob, ...]:
        with self._lock:
            with self._pool.connection() as conn:
                rows = conn.execute("SELECT job_json FROM ai_review_jobs").fetchall()
            pending: list[ReviewJob] = []
            for row in rows:
                job = ReviewJob.model_validate_json(row[0])
                if job.status == ReviewJobStatus.PROCESSING:
                    recovered_status = (
                        ReviewJobStatus.RETRY_PENDING
                        if job.attempt_count < job.max_attempts
                        else ReviewJobStatus.FAILED
                    )
                    job = job.model_copy(
                        update={
                            "status": recovered_status,
                            "failure_reason": "review worker interrupted before completion",
                            "updated_at": utc_now(),
                        }
                    )
                    self._save_job(job)
                if job.status in {ReviewJobStatus.QUEUED, ReviewJobStatus.RETRY_PENDING}:
                    pending.append(_copy_job(job))
            return tuple(pending)

    def record_disposition(self, job_id: UUID, request: ReviewDispositionRequest) -> ReviewDisposition:
        with self._lock:
            job = self._require_job(job_id)
            InMemoryReviewRepository._validate_disposition(job, request)
            disposition = ReviewDisposition(job_id=job_id, **request.model_dump())
            with self._pool.connection() as conn:
                conn.execute(
                    "INSERT INTO ai_review_dispositions (id, job_id, disposition_json) VALUES (%s, %s, %s)",
                    (str(disposition.id), str(job_id), disposition.model_dump_json()),
                )
                conn.commit()
            return disposition

    def list_dispositions(self, job_id: UUID) -> tuple[ReviewDisposition, ...]:
        with self._pool.connection() as conn:
            rows = conn.execute(
                "SELECT disposition_json FROM ai_review_dispositions WHERE job_id = %s ORDER BY id",
                (str(job_id),),
            ).fetchall()
        return tuple(ReviewDisposition.model_validate_json(row[0]) for row in rows)

    def _job_for_event(self, event_id: UUID) -> ReviewJob | None:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT job_json FROM ai_review_jobs WHERE event_id = %s", (str(event_id),)
            )
            row = cur.fetchone()
        return ReviewJob.model_validate_json(row[0]) if row else None

    def _require_job(self, job_id: UUID) -> ReviewJob:
        job = self.get_job(job_id)
        if not job:
            raise KeyError(f"review job {job_id} was not found")
        return job

    def _save_job(self, job: ReviewJob) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "UPDATE ai_review_jobs SET job_json = %s WHERE id = %s",
                (job.model_dump_json(), str(job.id)),
            )
            conn.commit()

    def _create_schema(self) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ai_review_jobs (
                    id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL UNIQUE,
                    job_json JSONB NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ai_review_dispositions (
                    id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL REFERENCES ai_review_jobs(id),
                    disposition_json JSONB NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ai_review_dispositions_job_id
                    ON ai_review_dispositions(job_id)
                """
            )
            conn.commit()
