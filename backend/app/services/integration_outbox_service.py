"""Durable, lease-based dispatch for minimized integration events.

The API records an intent in the same transaction as its domain change.  A
worker may later claim it conditionally and perform the slow network request
without holding an HTTP request or database transaction open.
"""

from __future__ import annotations

import os
import socket
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.approval_history import ApprovalHistory
from app.core.database import get_session_local
from app.models.expense_report import ExpenseReport
from app.models.integration_outbox import IntegrationOutbox


_LEASE_SECONDS = 60
_MAX_ATTEMPTS = 8
_AI_REVIEW_EVENT_TYPES = ("ai_review.requested", "ai_review.human_disposition")


def utcnow() -> datetime:
    return datetime.now(UTC)


def _worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:12]}"


def _enqueue(
    db: Session,
    *,
    event_type: str,
    aggregate_id: uuid.UUID,
    dedupe_key: str,
    payload: dict[str, object],
) -> IntegrationOutbox:
    """Insert one idempotent intent without committing its parent transaction."""

    existing = db.scalar(select(IntegrationOutbox).where(IntegrationOutbox.dedupe_key == dedupe_key))
    if existing is not None:
        return existing
    row = IntegrationOutbox(
        event_type=event_type,
        aggregate_type="expense_report",
        aggregate_id=aggregate_id,
        dedupe_key=dedupe_key,
        payload_json=payload,
        status="pending",
        attempt_count=0,
        available_at=utcnow(),
    )
    try:
        # A savepoint makes a duplicate-key race harmless without rolling back
        # the report submission transaction that created this intent.
        with db.begin_nested():
            db.add(row)
            db.flush()
    except IntegrityError:
        # A concurrent retry of the same report is safe: the unique dedupe
        # key is the authority and the caller's surrounding transaction stays
        # responsible for handling any unrelated integrity error.
        return db.scalar(select(IntegrationOutbox).where(IntegrationOutbox.dedupe_key == dedupe_key))
    return row


def enqueue_ai_review(db: Session, report: ExpenseReport) -> IntegrationOutbox | None:
    """Stage one minimized AI-review intent without performing network I/O."""

    from app.services import ai_review_client

    if ai_review_client._service_url() is None:
        return None
    event = ai_review_client.build_review_event(db, report)
    if event is None:
        return None
    return _enqueue(
        db,
        event_type="ai_review.requested",
        aggregate_id=report.id,
        dedupe_key=f"ai_review:{event['event_id']}",
        payload=event,
    )


def enqueue_human_disposition(
    db: Session,
    report: ExpenseReport,
    reviewer_id: uuid.UUID | str,
    action: str,
    remarks: str | None,
) -> IntegrationOutbox | None:
    """Persist an advisory disposition with the authoritative human decision."""

    from app.services import ai_review_client

    event = ai_review_client.build_human_disposition_event(report, reviewer_id, action, remarks)
    if event is None:
        return None
    # ``act_on_report(..., commit=False)`` flushes the history row before this
    # function is called.  Its immutable ID gives retries a stable key even
    # when the same approver later handles a resubmitted report.
    decision_id = db.scalar(
        select(ApprovalHistory.id)
        .where(
            ApprovalHistory.expense_report_id == report.id,
            ApprovalHistory.performed_by == reviewer_id,
            ApprovalHistory.action == action,
            ApprovalHistory.is_deleted.is_(False),
        )
        .order_by(ApprovalHistory.performed_at.desc(), ApprovalHistory.created_at.desc())
        .limit(1)
    )
    if decision_id is None:
        raise RuntimeError("Approval history was not available for disposition outbox enqueue")
    return _enqueue(
        db,
        event_type="ai_review.human_disposition",
        aggregate_id=report.id,
        dedupe_key=f"ai_disposition:{decision_id}",
        payload=event,
    )


def _claim(db: Session, *, limit: int, worker: str) -> list[uuid.UUID]:
    now = utcnow()
    candidate_ids = list(
        db.scalars(
            select(IntegrationOutbox.id)
            .where(
                IntegrationOutbox.event_type.in_(_AI_REVIEW_EVENT_TYPES),
                IntegrationOutbox.attempt_count < _MAX_ATTEMPTS,
                IntegrationOutbox.available_at <= now,
                or_(
                    IntegrationOutbox.status.in_(("pending", "retry")),
                    and_(
                        IntegrationOutbox.status == "processing",
                        IntegrationOutbox.locked_until.is_not(None),
                        IntegrationOutbox.locked_until < now,
                    ),
                ),
            )
            .order_by(IntegrationOutbox.created_at.asc())
            .limit(limit)
        )
    )
    claimed: list[uuid.UUID] = []
    for row_id in candidate_ids:
        changed = db.execute(
            update(IntegrationOutbox)
            .where(
                IntegrationOutbox.id == row_id,
                IntegrationOutbox.available_at <= now,
                or_(
                    IntegrationOutbox.status.in_(("pending", "retry")),
                    and_(
                        IntegrationOutbox.status == "processing",
                        IntegrationOutbox.locked_until.is_not(None),
                        IntegrationOutbox.locked_until < now,
                    ),
                ),
            )
            .values(
                status="processing",
                locked_by=worker,
                locked_until=now + timedelta(seconds=_LEASE_SECONDS),
                attempt_count=IntegrationOutbox.attempt_count + 1,
            )
        ).rowcount
        if changed:
            claimed.append(row_id)
    db.commit()
    return claimed


def _retry_at(attempt_count: int) -> datetime:
    return utcnow() + timedelta(seconds=min(3600, 2 ** min(attempt_count, 10)))


def _safe_error(exc: Exception) -> str:
    return f"{type(exc).__name__}: {' '.join(str(exc).split())}"[:500]


def deliver_pending_ai_reviews(db: Session | None = None, *, limit: int = 25) -> int:
    """Dispatch a bounded batch; safe to invoke from a scheduler or worker."""

    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    owns_session = db is None
    session = db or get_session_local()()
    worker = _worker_id()
    completed = 0
    try:
        for row_id in _claim(session, limit=limit, worker=worker):
            row = session.get(IntegrationOutbox, row_id)
            if row is None or row.locked_by != worker:
                continue
            try:
                from app.services import ai_review_client

                if row.event_type == "ai_review.requested":
                    job = ai_review_client._request("POST", "/v1/review-jobs", row.payload_json)
                    job_id = uuid.UUID(str(job["id"]))
                    report = session.get(ExpenseReport, row.aggregate_id)
                    if report is not None:
                        report.ai_review_job_id = job_id
                        report.ai_review_requested_at = utcnow()
                elif row.event_type == "ai_review.human_disposition":
                    report = session.get(ExpenseReport, row.aggregate_id)
                    job_id = str(report.ai_review_job_id) if report and report.ai_review_job_id else None
                    if job_id and row.payload_json.get("job_id") != job_id:
                        row.payload_json = {**row.payload_json, "job_id": job_id}
                    ai_review_client.deliver_human_disposition_event(row.payload_json, job_id=job_id)
                else:  # Defensive guard if a future event type bypasses claim filtering.
                    raise ValueError(f"Unsupported AI integration event type: {row.event_type}")
                row.status = "processed"
                row.processed_at = utcnow()
                row.locked_by = None
                row.locked_until = None
                row.last_error = None
                session.commit()
                completed += 1
            except Exception as exc:
                session.rollback()
                failed = session.get(IntegrationOutbox, row_id)
                if failed is None:
                    continue
                failed.status = "failed" if failed.attempt_count >= _MAX_ATTEMPTS else "retry"
                failed.available_at = _retry_at(failed.attempt_count)
                failed.locked_by = None
                failed.locked_until = None
                failed.last_error = _safe_error(exc)
                session.commit()
        return completed
    finally:
        if owns_session:
            session.close()
