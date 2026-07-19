"""Opt-in SMTP delivery and notification-side workflow helpers.

The reimbursement API persists in-app and email notification rows in the same
transaction as the business event.  This module deliberately keeps outbound
SMTP work outside that transaction: FastAPI may enqueue ``deliver_pending_email_notifications``
after the response, or a deployment can call it from a worker.  No SMTP client
is constructed unless ``EMAIL_DELIVERY_ENABLED=true``.
"""

from __future__ import annotations

import smtplib
import uuid
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from typing import Any

from fastapi import BackgroundTasks
from sqlalchemy import and_, or_, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_session_local
from app.models.approval_level import ApprovalLevel
from app.models.expense_report import ExpenseReport
from app.models.notification import Notification
from app.models.user import User
from app.services.notification_service import notify


def email_delivery_enabled() -> bool:
    """Return whether a worker is allowed to make an outbound SMTP connection."""

    return bool(getattr(get_settings(), "email_delivery_enabled", False))


def enqueue_pending_email_delivery(background_tasks: BackgroundTasks) -> bool:
    """Add the worker to a response only when external delivery is enabled.

    Returning ``False`` means no task was enqueued; it does not mean that the
    notification was lost.  Email rows stay pending for a later enabled worker.
    """

    if not email_delivery_enabled():
        return False
    background_tasks.add_task(deliver_pending_email_notifications)
    return True


def cancel_pending_approvals_for_withdrawal(db: Session, report: ExpenseReport) -> list[ApprovalLevel]:
    """Cancel outstanding approval tasks and notify every affected approver.

    This intentionally does not commit.  Calling it from the report withdrawal
    transaction makes the task cancellation and both in-app/email notification
    rows atomic.  A report service should replace its bulk cancellation with
    this helper before committing the withdrawal.
    """

    levels = (
        db.query(ApprovalLevel)
        .filter(
            ApprovalLevel.expense_report_id == report.id,
            ApprovalLevel.status.in_(("pending", "waiting")),
            ApprovalLevel.is_deleted.is_(False),
        )
        .order_by(ApprovalLevel.level_number)
        .all()
    )
    for level in levels:
        level.status = "cancelled"

    for approver_id in dict.fromkeys(level.approver_user_id for level in levels):
        notify(
            db,
            approver_id,
            "report_withdrawn",
            {
                "title": "Expense report withdrawn",
                "body": f"{report.title} was withdrawn. Your approval is no longer required.",
                "report_id": str(report.id),
                "type": "approval_cancelled",
            },
            channels=("in_app", "email"),
        )
    return levels


def _header_value(value: Any, fallback: str) -> str:
    """Normalize header text so untrusted report titles cannot inject headers."""

    normalized = " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())
    return normalized or fallback


def _message_for(notification: Notification, recipient: User, settings: Any) -> EmailMessage:
    payload = notification.payload_json or {}
    message = EmailMessage()
    message["From"] = _header_value(getattr(settings, "smtp_from", None), "no-reply@localhost")
    message["To"] = _header_value(recipient.email, "undisclosed-recipients:;")
    message["Subject"] = _header_value(payload.get("title"), notification.template_code.replace("_", " ").title())
    message["Message-ID"] = f"<{notification.id}@presidio-notifications>"
    body = str(payload.get("body") or "You have a reimbursement notification.").strip()
    message.set_content(f"{body}\n\nThis is an automated reimbursement notification.")
    return message


def _safe_delivery_error(exc: Exception) -> str:
    """Keep a useful, bounded diagnostic without leaking SMTP credentials."""

    detail = " ".join(str(exc).replace("\r", " ").replace("\n", " ").split())
    return f"{exc.__class__.__name__}: {detail}"[:500]


_LEASE_SECONDS = 120
_MAX_DELIVERY_ATTEMPTS = 8


def _claim_pending_email_notifications(db: Session, limit: int) -> list[tuple[uuid.UUID, uuid.UUID, str]]:
    """Claim due rows atomically and make abandoned claims reclaimable."""

    now = datetime.now(UTC)
    ready = or_(Notification.next_attempt_at.is_(None), Notification.next_attempt_at <= now)
    claimable = or_(
        and_(Notification.status.in_(("pending", "failed")), ready),
        and_(
            Notification.status == "sending",
            Notification.delivery_lease_expires_at.is_not(None),
            Notification.delivery_lease_expires_at < now,
        ),
    )
    rows = (
        db.query(Notification.id, Notification.recipient_user_id)
        .join(User, User.id == Notification.recipient_user_id)
        .filter(
            Notification.channel == "email",
            Notification.delivery_attempts < _MAX_DELIVERY_ATTEMPTS,
            Notification.is_deleted.is_(False),
            User.is_deleted.is_(False),
            User.status == "active",
            claimable,
        )
        .order_by(Notification.created_at.asc())
        .limit(limit)
        .all()
    )
    claimed: list[tuple[uuid.UUID, uuid.UUID, str]] = []
    for notification_id, recipient_id in rows:
        claim_token = uuid.uuid4().hex
        changed = db.execute(
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.delivery_attempts < _MAX_DELIVERY_ATTEMPTS,
                or_(
                    and_(Notification.status.in_(("pending", "failed")), ready),
                    and_(
                        Notification.status == "sending",
                        Notification.delivery_lease_expires_at.is_not(None),
                        Notification.delivery_lease_expires_at < now,
                    ),
                ),
            )
            .values(
                status="sending",
                delivery_error=None,
                delivery_claim_token=claim_token,
                delivery_claimed_at=now,
                delivery_lease_expires_at=now + timedelta(seconds=_LEASE_SECONDS),
                delivery_attempts=Notification.delivery_attempts + 1,
            )
        ).rowcount
        if changed:
            claimed.append((notification_id, recipient_id, claim_token))
    db.commit()
    return claimed


def _open_smtp(settings: Any) -> smtplib.SMTP:
    smtp = smtplib.SMTP(
        getattr(settings, "smtp_host", "localhost"),
        int(getattr(settings, "smtp_port", 1025)),
        timeout=float(getattr(settings, "smtp_timeout_seconds", 10.0)),
    )
    smtp.ehlo()
    if bool(getattr(settings, "smtp_use_tls", False)):
        smtp.starttls()
        smtp.ehlo()
    username = getattr(settings, "smtp_user", None)
    if username:
        smtp.login(username, getattr(settings, "smtp_password", None) or "")
    return smtp


def _mark_delivery(
    db: Session,
    notification_id: uuid.UUID,
    claim_token: str,
    *,
    sent: bool,
    error: str | None = None,
) -> None:
    """Finish only a lease owned by this worker, preventing stale writes."""

    notification = db.get(Notification, notification_id)
    if notification is None or notification.delivery_claim_token != claim_token:
        return
    now = datetime.now(UTC)
    if sent:
        notification.status = "sent"
        notification.sent_at = now
        notification.delivery_error = None
        notification.next_attempt_at = None
    else:
        notification.status = "failed"
        notification.sent_at = None
        notification.delivery_error = error
        notification.next_attempt_at = (
            now + timedelta(seconds=min(3600, 2 ** min(notification.delivery_attempts, 10)))
            if notification.delivery_attempts < _MAX_DELIVERY_ATTEMPTS
            else None
        )
    notification.delivery_claim_token = None
    notification.delivery_claimed_at = None
    notification.delivery_lease_expires_at = None
    db.commit()


def _use_azure_email(settings: Any) -> bool:
    """Azure Communication Services is preferred when configured."""
    return bool(getattr(settings, "azure_communication_connection_string", ""))


def deliver_pending_email_notifications(db: Session | None = None, *, limit: int = 100) -> int:
    """Attempt a bounded batch of queued emails via Azure or SMTP fallback.

    Production uses Azure Communication Services. Local dev uses SMTP/MailHog.
    """

    if limit < 1:
        raise ValueError("limit must be at least 1")
    settings = get_settings()
    if not bool(getattr(settings, "email_delivery_enabled", False)):
        return 0

    owns_session = db is None
    session = db or get_session_local()()
    claimed: list[tuple[uuid.UUID, uuid.UUID, str]] = []
    sent = 0
    try:
        claimed = _claim_pending_email_notifications(session, limit)
        if not claimed:
            return 0

        if _use_azure_email(settings):
            sent = _deliver_via_azure(session, claimed, settings)
        else:
            sent = _deliver_via_smtp(session, claimed, settings)
        return sent
    finally:
        if owns_session:
            session.close()


def _deliver_via_azure(
    session: Session,
    claimed: list[tuple[uuid.UUID, uuid.UUID, str]],
    settings: Any,
) -> int:
    """Send emails through Azure Communication Services."""
    from app.services.azure_email_service import AzureEmailSender

    sender_address = getattr(settings, "azure_communication_sender", "") or getattr(settings, "smtp_from", "no-reply@presidio.com")
    try:
        azure_sender = AzureEmailSender(
            connection_string=settings.azure_communication_connection_string,
            sender_address=sender_address,
        )
    except Exception as exc:
        error = _safe_delivery_error(exc)
        for notification_id, _, claim_token in claimed:
            _mark_delivery(session, notification_id, claim_token, sent=False, error=error)
        return 0

    sent = 0
    for notification_id, recipient_id, claim_token in claimed:
        notification = session.get(Notification, notification_id)
        recipient = session.get(User, recipient_id)
        if notification is None or recipient is None:
            continue
        try:
            message = _message_for(notification, recipient, settings)
            azure_sender.send(message)
        except Exception as exc:
            _mark_delivery(session, notification_id, claim_token, sent=False, error=_safe_delivery_error(exc))
        else:
            _mark_delivery(session, notification_id, claim_token, sent=True)
            sent += 1
    return sent


def _deliver_via_smtp(
    session: Session,
    claimed: list[tuple[uuid.UUID, uuid.UUID, str]],
    settings: Any,
) -> int:
    """Send emails through SMTP (local development / MailHog fallback)."""
    smtp: smtplib.SMTP | None = None
    sent = 0
    try:
        smtp = _open_smtp(settings)
    except (OSError, smtplib.SMTPException, ValueError) as exc:
        error = _safe_delivery_error(exc)
        for notification_id, _, claim_token in claimed:
            _mark_delivery(session, notification_id, claim_token, sent=False, error=error)
        return 0

    try:
        for notification_id, recipient_id, claim_token in claimed:
            notification = session.get(Notification, notification_id)
            recipient = session.get(User, recipient_id)
            if notification is None or recipient is None:
                continue
            try:
                smtp.send_message(_message_for(notification, recipient, settings))
            except (OSError, smtplib.SMTPException, ValueError) as exc:
                _mark_delivery(session, notification_id, claim_token, sent=False, error=_safe_delivery_error(exc))
            else:
                _mark_delivery(session, notification_id, claim_token, sent=True)
                sent += 1
    finally:
        try:
            smtp.quit()
        except (OSError, smtplib.SMTPException):
            pass
    return sent
