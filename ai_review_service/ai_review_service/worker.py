"""Bounded in-process worker used by the isolated local AI deployment.

This module deliberately owns no reimbursement state.  It only receives an
opaque review-job ID and calls the AI service's own persistence/service
boundary.  Production can replace this convenience worker with a queue
consumer while retaining exactly the same ``ExpenseReviewService.process``
operation.
"""

from __future__ import annotations

import asyncio
import threading
from uuid import UUID

from .contracts import ReviewJobStatus
from .service import ExpenseReviewService


class LocalReviewWorker:
    """Process one job at a time per ID with bounded retry handling.

    The FastAPI endpoint schedules this object through ``BackgroundTasks`` so
    accepting an event remains asynchronous for real clients.  The in-memory
    guard prevents duplicate event delivery from running the same job twice in
    one service process; repository claiming remains the durable authority.
    """

    def __init__(
        self,
        service: ExpenseReviewService,
        *,
        max_concurrency: int,
        retry_delay_seconds: float,
    ) -> None:
        self._service = service
        self._retry_delay_seconds = retry_delay_seconds
        self._active_job_ids: set[UUID] = set()
        self._lock = threading.Lock()
        self._capacity = asyncio.Semaphore(max_concurrency)

    async def process(self, job_id: UUID) -> None:
        """Drive a queued job to a terminal state without raising to callers."""

        with self._lock:
            if job_id in self._active_job_ids:
                return
            self._active_job_ids.add(job_id)

        try:
            async with self._capacity:
                while True:
                    try:
                        job = await self._service.process(job_id)
                    except KeyError:
                        return

                    if job.status != ReviewJobStatus.RETRY_PENDING:
                        return
                    await asyncio.sleep(self._retry_delay_seconds)
        finally:
            with self._lock:
                self._active_job_ids.discard(job_id)
