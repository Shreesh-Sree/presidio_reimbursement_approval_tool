# Email notification delivery

The application always stores in-app notifications. Email rows are also queued
for report status events, but no SMTP connection is made until delivery is
explicitly enabled:

```dotenv
EMAIL_DELIVERY_ENABLED=true
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=mailer@example.com
SMTP_PASSWORD=replace-with-a-secret
SMTP_FROM=no-reply@example.com
SMTP_USE_TLS=true
SMTP_TIMEOUT_SECONDS=10
```

`app.services.notification_delivery_service.deliver_pending_email_notifications`
is safe to invoke from a worker, scheduler, or FastAPI background task. It
claims a bounded batch of pending rows before connecting to SMTP, records
`sent` or `failed` state, and leaves disabled delivery rows untouched. Do not
invoke it inside a request transaction.

For report submission, approval decisions, and withdrawals, enqueue
`enqueue_pending_email_delivery(background_tasks)` after the corresponding
service commits. For withdrawals, replace the bulk approval-level cancellation
with `cancel_pending_approvals_for_withdrawal(db, report)` before committing so
each cancelled approver receives an in-app and queued-email notification in the
same transaction.
