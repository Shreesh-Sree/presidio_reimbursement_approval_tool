# Backend security and operations runbook

This runbook covers the operational actions required by the tenant-safety,
durable-delivery, receipt-privacy, and Supabase authentication changes. It is
intentionally deployment-specific: do not place production values in example
files or source control.

## Release procedure for migration 009

Migration `009_tenant_workflows_catalogs_and_outbox` moves workflow rules,
expense categories, and vendors to required organization ownership. This is a
contract migration, not a zero-downtime schema change. An older application
binary can attempt to insert rows without the new ownership field.

For this release, schedule a short write-maintenance window rather than
running old and new binaries concurrently:

1. Take a tested PostgreSQL backup and record the currently deployed image and
   Alembic revision.
2. Drain API traffic or enable maintenance mode for every write endpoint. Stop
   workers which can create or edit catalog/workflow rows.
3. Run `cd backend && alembic upgrade head` with the production database URL.
4. Deploy the matching backend and worker image, then run a smoke test for a
   report submission, workflow lookup, category/vendor administration, and an
   attachment download in a second tenant.
5. Check `cd backend && alembic current` and `alembic check`, then re-enable
   writes.

Do not use `alembic downgrade` as the primary production recovery mechanism
after the new binary has accepted writes. Restore the verified pre-migration
backup or use a reviewed, data-preserving recovery plan. A future true
zero-downtime rollout must be split into separately deployed expand and
contract releases; applying `upgrade head` before the new application binary
is not sufficient.

## Durable background work

Run the worker in a platform scheduler or job runner, for example every minute:

```bash
cd backend
python -m app.worker --once
```

It performs three bounded, lease-claimed tasks: overdue-approval escalation,
queued email delivery, and AI-review outbox delivery. Multiple workers are
safe; do not run an in-process infinite loop in the web application.

Alert on rows that reach `failed` after their retry budget in
`integration_outbox` and email notifications, as well as a scheduler job that
has not completed successfully. Email transport is at-least-once at the SMTP
boundary (with a stable message ID to help providers deduplicate); the durable
database state prevents a worker crash from silently losing queued work.

The AI outbox holds only minimized request/disposition payloads. Human
approval remains authoritative even if the advisory AI service is unavailable;
the worker retries the advisory disposition independently.

## Receipt data and external AI egress

Receipt OCR text is redacted and bounded before it can leave the
receipt-intelligence service. Rule-based analysis remains available while
external egress is disabled.

External Groq processing requires both controls below:

1. The backend must explicitly list the organization UUID in
   `RECEIPT_INTELLIGENCE_EXTERNAL_PROVIDER_ORGANIZATION_IDS`.
2. The receipt service must set
   `RECEIPT_INTELLIGENCE_GROQ_EXTERNAL_EGRESS_ENABLED=true` and have a valid
   provider credential.

Keep both controls disabled by default. Before enabling them, obtain and record
the organization-level approval, validate the provider DPA/data-residency and
retention terms, document the applicable legal basis, and confirm that the
provider account has no training/retention setting inconsistent with policy.
Re-test the redaction boundary with representative receipts after any provider
or prompt change. Never log raw OCR text, receipt images, provider tokens, or
the organization allowlist.

Default limits are 10 MiB for receipts, 15 MiB for policy documents, 1 MiB for
bulk-user CSVs, 2,000 external text characters, and 20 million image pixels.
Set ingress/proxy body limits to the same maximum plus multipart overhead, and
retain the application limits as the authority because clients can omit or lie
about `Content-Length`.

## Supabase email identity operations

Supabase is the source of truth for OAuth identity and verified email. Do not
change an OAuth user's application email directly. Have the user change and
verify the email with the Supabase-supported provider flow, then sign in again;
the backend reconciles the verified subject email to the linked application
account when it is conflict-free.

Before promotion, verify the configured Supabase project URL/JWT verification
material, allowed redirect URLs, provider redirect configuration, and the
bootstrap administrator identity. Follow the existing
`supabase-production-promotion.md` checklist for provider-side changes. Keep
service-role credentials in the deployment secret store only.

## Public access requests and abuse controls

Public access-request responses are deliberately generic so they do not reveal
whether an email has an account or a pending request. The application limiter
is a local process guard, not a distributed anti-abuse control. Production must
also configure a gateway/WAF rate limit keyed by IP and request fingerprint,
an abuse alert, and an appropriate CAPTCHA or equivalent challenge before
opening this endpoint broadly. Review administrator access to
`access_request:manage` regularly.

## Request execution model

The database/storage/OCR/advisory API handlers are synchronous FastAPI
handlers, so their existing synchronous SQLAlchemy and HTTP/storage clients run
in FastAPI's threadpool rather than blocking an event-loop worker. Slow,
retryable AI delivery is additionally handed to the durable worker. The chat
route remains asynchronous because it intentionally uses an async HTTP client.

This is a consistent threadpool model, not an `AsyncSession` migration. Size
the web worker/threadpool after a delayed-dependency load test, and keep future
handlers in one model: synchronous when using the current SQLAlchemy/storage
clients, or fully async only after their dependencies are migrated too.
