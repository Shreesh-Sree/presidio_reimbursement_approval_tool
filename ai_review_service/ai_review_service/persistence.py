"""Persistence boundary owned exclusively by the AI review service.

The implementation uses a separate SQLite file for a deployable local default.
Production can replace this repository through the ``ReviewRepository``
protocol, pointed at an AI-service-owned datastore.  It must never reuse the
core reimbursement database or its ORM models.
"""

from __future__ import annotations

from pathlib import Path
import sqlite3
import threading
from typing import Protocol
from uuid import UUID

from .contracts import (
    ExpenseReviewRequested,
    ReviewDisposition,
    ReviewDispositionRequest,
    ReviewJob,
    ReviewJobStatus,
    ReviewResult,
    utc_now,
)


class ReviewRepository(Protocol):
    def enqueue(self, event: ExpenseReviewRequested, *, max_attempts: int) -> ReviewJob: ...

    def get_job(self, job_id: UUID) -> ReviewJob | None: ...

    def claim(self, job_id: UUID) -> ReviewJob | None: ...

    def complete(self, job_id: UUID, result: ReviewResult) -> ReviewJob: ...

    def retry_or_fail(self, job_id: UUID, failure_reason: str) -> ReviewJob: ...

    def record_disposition(
        self, job_id: UUID, request: ReviewDispositionRequest
    ) -> ReviewDisposition: ...

    def list_dispositions(self, job_id: UUID) -> tuple[ReviewDisposition, ...]: ...


def _copy_job(job: ReviewJob) -> ReviewJob:
    return job.model_copy(deep=True)


class InMemoryReviewRepository:
    """Thread-safe local/test repository implementing the isolated boundary."""

    def __init__(self) -> None:
        self._jobs: dict[UUID, ReviewJob] = {}
        self._event_index: dict[UUID, UUID] = {}
        self._dispositions: dict[UUID, list[ReviewDisposition]] = {}
        self._lock = threading.RLock()

    def enqueue(self, event: ExpenseReviewRequested, *, max_attempts: int) -> ReviewJob:
        with self._lock:
            if existing_id := self._event_index.get(event.event_id):
                return _copy_job(self._jobs[existing_id])
            job = ReviewJob(event=event, max_attempts=max_attempts)
            self._jobs[job.id] = job
            self._event_index[event.event_id] = job.id
            return _copy_job(job)

    def get_job(self, job_id: UUID) -> ReviewJob | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return _copy_job(job) if job else None

    def claim(self, job_id: UUID) -> ReviewJob | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            if job.status not in {ReviewJobStatus.QUEUED, ReviewJobStatus.RETRY_PENDING}:
                return _copy_job(job)
            claimed = job.model_copy(
                update={
                    "status": ReviewJobStatus.PROCESSING,
                    "attempt_count": job.attempt_count + 1,
                    "updated_at": utc_now(),
                    "failure_reason": None,
                }
            )
            self._jobs[job_id] = claimed
            return _copy_job(claimed)

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
            self._jobs[job_id] = completed
            return _copy_job(completed)

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
            self._jobs[job_id] = updated
            return _copy_job(updated)

    def record_disposition(
        self, job_id: UUID, request: ReviewDispositionRequest
    ) -> ReviewDisposition:
        with self._lock:
            job = self._require_job(job_id)
            self._validate_disposition(job, request)
            disposition = ReviewDisposition(job_id=job_id, **request.model_dump())
            self._dispositions.setdefault(job_id, []).append(disposition)
            return disposition.model_copy(deep=True)

    def list_dispositions(self, job_id: UUID) -> tuple[ReviewDisposition, ...]:
        with self._lock:
            return tuple(item.model_copy(deep=True) for item in self._dispositions.get(job_id, []))

    def _require_job(self, job_id: UUID) -> ReviewJob:
        job = self._jobs.get(job_id)
        if not job:
            raise KeyError(f"review job {job_id} was not found")
        return job

    @staticmethod
    def _validate_disposition(job: ReviewJob, request: ReviewDispositionRequest) -> None:
        if job.status != ReviewJobStatus.COMPLETED or not job.result:
            raise ValueError("a human disposition requires a completed advisory review")
        known_ids = {finding.id for finding in job.result.evaluation.findings}
        unknown_ids = set(request.finding_ids) - known_ids
        if unknown_ids:
            raise ValueError("the disposition references findings outside this review")


class SqliteReviewRepository(InMemoryReviewRepository):
    """Durable repository in an AI-service-owned SQLite database file.

    The format stores only the already-minimized event and advisory output.  It
    is deliberately not a SQLAlchemy model and cannot be joined to core tables.
    """

    def __init__(self, path: str | Path) -> None:
        super().__init__()
        if str(path).startswith(("postgresql://", "postgres://")):
            raise ValueError("AI review persistence must use its own datastore, not the core database")
        self._path = str(path)
        if self._path != ":memory:":
            Path(self._path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self._path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._create_schema()

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def enqueue(self, event: ExpenseReviewRequested, *, max_attempts: int) -> ReviewJob:
        with self._lock:
            existing = self._job_for_event(event.event_id)
            if existing:
                return existing
            job = ReviewJob(event=event, max_attempts=max_attempts)
            self._connection.execute(
                "INSERT INTO ai_review_jobs (id, event_id, job_json) VALUES (?, ?, ?)",
                (str(job.id), str(event.event_id), job.model_dump_json()),
            )
            self._connection.commit()
            return _copy_job(job)

    def get_job(self, job_id: UUID) -> ReviewJob | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT job_json FROM ai_review_jobs WHERE id = ?", (str(job_id),)
            ).fetchone()
            return ReviewJob.model_validate_json(row["job_json"]) if row else None

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
            job = self._require_sqlite_job(job_id)
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
            job = self._require_sqlite_job(job_id)
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

    def record_disposition(
        self, job_id: UUID, request: ReviewDispositionRequest
    ) -> ReviewDisposition:
        with self._lock:
            job = self._require_sqlite_job(job_id)
            self._validate_disposition(job, request)
            disposition = ReviewDisposition(job_id=job_id, **request.model_dump())
            self._connection.execute(
                "INSERT INTO ai_review_dispositions (id, job_id, disposition_json) VALUES (?, ?, ?)",
                (str(disposition.id), str(job_id), disposition.model_dump_json()),
            )
            self._connection.commit()
            return disposition

    def list_dispositions(self, job_id: UUID) -> tuple[ReviewDisposition, ...]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT disposition_json FROM ai_review_dispositions WHERE job_id = ? ORDER BY rowid",
                (str(job_id),),
            ).fetchall()
            return tuple(ReviewDisposition.model_validate_json(row["disposition_json"]) for row in rows)

    def _job_for_event(self, event_id: UUID) -> ReviewJob | None:
        row = self._connection.execute(
            "SELECT job_json FROM ai_review_jobs WHERE event_id = ?", (str(event_id),)
        ).fetchone()
        return ReviewJob.model_validate_json(row["job_json"]) if row else None

    def _require_sqlite_job(self, job_id: UUID) -> ReviewJob:
        job = self.get_job(job_id)
        if not job:
            raise KeyError(f"review job {job_id} was not found")
        return job

    def _save_job(self, job: ReviewJob) -> None:
        self._connection.execute(
            "UPDATE ai_review_jobs SET job_json = ? WHERE id = ?",
            (job.model_dump_json(), str(job.id)),
        )
        self._connection.commit()

    def _create_schema(self) -> None:
        with self._lock:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS ai_review_jobs (
                    id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL UNIQUE,
                    job_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ai_review_dispositions (
                    id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    disposition_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_ai_review_dispositions_job_id
                    ON ai_review_dispositions(job_id);
                """
            )
            self._connection.commit()
