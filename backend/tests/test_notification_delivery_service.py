"""Focused coverage for opt-in email delivery and withdrawal notifications."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from fastapi import BackgroundTasks

from app.models.approval_level import ApprovalLevel
from app.models.notification import Notification
from app.models.user import User
from app.services import notification_delivery_service, notification_service
from app.services.report_service import create_draft


def _settings(*, enabled: bool, use_tls: bool = False):
    return SimpleNamespace(
        email_delivery_enabled=enabled,
        smtp_host="smtp.test",
        smtp_port=2525,
        smtp_user="mailer",
        smtp_password="not-a-real-secret",
        smtp_from="no-reply@example.com",
        smtp_use_tls=use_tls,
        smtp_timeout_seconds=2.0,
    )


def _approver(db, seeded_user, suffix: str) -> User:
    approver = User(
        organization_id=seeded_user.organization_id,
        department_id=seeded_user.department_id,
        employee_number=f"APP-{suffix}",
        username=f"approver-{suffix}",
        email=f"approver-{suffix}@example.com",
        password_hash=seeded_user.password_hash,
        full_name=f"Approver {suffix}",
        status="active",
    )
    db.add(approver)
    db.flush()
    return approver


def test_disabled_delivery_never_constructs_smtp_client(db, seeded_user, monkeypatch):
    email_notification = notification_service.notify(
        db,
        seeded_user.id,
        "report_approved_pending_payment",
        {"title": "Approved", "body": "Your report is approved."},
        channels=("email",),
    )[0]
    db.commit()

    monkeypatch.setattr(notification_delivery_service, "get_settings", lambda: _settings(enabled=False))

    def should_not_connect(*_args, **_kwargs):
        raise AssertionError("SMTP must remain unused when EMAIL_DELIVERY_ENABLED is false")

    monkeypatch.setattr(notification_delivery_service.smtplib, "SMTP", should_not_connect)

    assert notification_delivery_service.deliver_pending_email_notifications(db) == 0
    db.refresh(email_notification)
    assert email_notification.status == "pending"
    assert email_notification.sent_at is None


def test_enabled_delivery_sends_queued_email_and_marks_notification_sent(db, seeded_user, monkeypatch):
    email_notification = notification_service.notify(
        db,
        seeded_user.id,
        "report_approved_pending_payment",
        {"title": "Report approved", "body": "Your report is pending payment."},
        channels=("email",),
    )[0]
    db.commit()

    class FakeSMTP:
        messages = []
        starttls_called = False
        login_args = None

        def __init__(self, host, port, timeout):
            assert (host, port, timeout) == ("smtp.test", 2525, 2.0)

        def ehlo(self):
            return None

        def starttls(self):
            type(self).starttls_called = True

        def login(self, username, password):
            type(self).login_args = (username, password)

        def send_message(self, message):
            type(self).messages.append(message)

        def quit(self):
            return None

    monkeypatch.setattr(notification_delivery_service, "get_settings", lambda: _settings(enabled=True, use_tls=True))
    monkeypatch.setattr(notification_delivery_service.smtplib, "SMTP", FakeSMTP)

    assert notification_delivery_service.deliver_pending_email_notifications(db) == 1
    db.refresh(email_notification)
    assert email_notification.status == "sent"
    assert email_notification.sent_at is not None
    assert email_notification.delivery_error is None
    assert FakeSMTP.starttls_called is True
    assert FakeSMTP.login_args == ("mailer", "not-a-real-secret")
    assert FakeSMTP.messages[0]["To"] == seeded_user.email
    assert FakeSMTP.messages[0]["Subject"] == "Report approved"


def test_smtp_failure_marks_claimed_email_failed_without_raising(db, seeded_user, monkeypatch):
    email_notification = notification_service.notify(
        db,
        seeded_user.id,
        "report_submitted_for_approval",
        {"title": "Needs review", "body": "A report is ready."},
        channels=("email",),
    )[0]
    db.commit()

    def unavailable_smtp(*_args, **_kwargs):
        raise OSError("mail relay unavailable")

    monkeypatch.setattr(notification_delivery_service, "get_settings", lambda: _settings(enabled=True))
    monkeypatch.setattr(notification_delivery_service.smtplib, "SMTP", unavailable_smtp)

    assert notification_delivery_service.deliver_pending_email_notifications(db) == 0
    db.refresh(email_notification)
    assert email_notification.status == "failed"
    assert "OSError" in (email_notification.delivery_error or "")
    assert "mail relay unavailable" in (email_notification.delivery_error or "")


def test_enqueue_only_adds_background_worker_when_delivery_is_enabled(monkeypatch):
    tasks = BackgroundTasks()
    monkeypatch.setattr(notification_delivery_service, "get_settings", lambda: _settings(enabled=False))
    assert notification_delivery_service.enqueue_pending_email_delivery(tasks) is False
    assert tasks.tasks == []

    monkeypatch.setattr(notification_delivery_service, "get_settings", lambda: _settings(enabled=True))
    assert notification_delivery_service.enqueue_pending_email_delivery(tasks) is True
    assert len(tasks.tasks) == 1
    assert tasks.tasks[0].func is notification_delivery_service.deliver_pending_email_notifications


def test_expired_delivery_lease_is_safely_reclaimed(db, seeded_user):
    notification = notification_service.notify(
        db,
        seeded_user.id,
        "report_submitted_for_approval",
        {"title": "Needs review"},
        channels=("email",),
    )[0]
    db.commit()

    first = notification_delivery_service._claim_pending_email_notifications(db, 1)
    assert len(first) == 1
    first_token = first[0][2]
    db.refresh(notification)
    notification.delivery_lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()

    second = notification_delivery_service._claim_pending_email_notifications(db, 1)
    assert len(second) == 1
    assert second[0][0] == notification.id
    assert second[0][2] != first_token
    db.refresh(notification)
    assert notification.status == "sending"
    assert notification.delivery_attempts == 2


def test_withdrawal_cancellation_notifies_each_pending_or_waiting_approver(db, seeded_user):
    first = _approver(db, seeded_user, "one")
    second = _approver(db, seeded_user, "two")
    report = create_draft(db, seeded_user.id, seeded_user.department_id, "Cancelled client visit")
    report.status = "submitted"
    db.add_all(
        [
            ApprovalLevel(
                expense_report_id=report.id,
                approver_user_id=first.id,
                level_number=1,
                status="pending",
            ),
            ApprovalLevel(
                expense_report_id=report.id,
                approver_user_id=second.id,
                level_number=2,
                status="waiting",
            ),
        ]
    )
    db.commit()

    cancelled = notification_delivery_service.cancel_pending_approvals_for_withdrawal(db, report)
    db.commit()

    assert [level.status for level in cancelled] == ["cancelled", "cancelled"]
    notifications = (
        db.query(Notification)
        .filter(Notification.template_code == "report_withdrawn")
        .order_by(Notification.channel, Notification.recipient_user_id)
        .all()
    )
    assert {(notification.recipient_user_id, notification.channel) for notification in notifications} == {
        (first.id, "email"),
        (first.id, "in_app"),
        (second.id, "email"),
        (second.id, "in_app"),
    }
    assert all(notification.payload_json["report_id"] == str(report.id) for notification in notifications)
