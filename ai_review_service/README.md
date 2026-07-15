# AI Expense Review Service

This is a separately deployable, advisory-only service for submitted expense
reports. It intentionally does **not** import the reimbursement API, its ORM,
or its database models. It does not approve, reject, route, or mutate a claim.
An authorized human remains responsible for every workflow decision.

## Boundary

```text
core reimbursement API -- expense_report.submitted event --> AI review service
                                                               |
                                                     separate AI datastore
                                                               |
core approver UI <-- advisory result + human disposition ------+
```

The core service publishes a versioned `ExpenseReviewRequested` event after it
has frozen the report's policy snapshot. The event is idempotent by `event_id`.
This service records its own `ai_review_jobs` and `ai_review_dispositions` in
`AI_REVIEW_DATABASE_PATH` (SQLite by default). It refuses a PostgreSQL URL to
make accidental reuse of the reimbursement database impossible. A production
repository can implement `ReviewRepository` for an AI-service-owned database.

## What is reviewed

The deterministic evaluator runs before any model call and can flag:

- per-item, per-report/category, and vendor-specific policy caps;
- receipt thresholds and unconfigured categories;
- matching receipt digests or duplicate line signatures; and
- category totals above an aggregate, privacy-safe historical baseline.

An optional Gemini or Groq adapter receives only aggregate totals and sanitized
findings. It never receives a report/user ID, employee name/email, vendor
value, description, receipt digest, receipt file, URL, OCR output, or raw
policy document. It drafts a concise summary; the recommendation is advisory.
If a selected provider times out or fails, it retries with a bounded backoff
and then uses a deterministic rule-based narrative. Provider errors are not
stored in a job.

## Event contract

Use opaque UUID/HMAC-style references, vendor/category codes, receipt hashes,
and a policy snapshot. Do not include profiles, document content, display
labels, emails, phone numbers, file names, or signed URLs.

```json
{
  "event_id": "b37f6618-a4ae-4c6d-a4dd-507e15b92f14",
  "event_type": "expense_report.submitted",
  "event_version": "1.0",
  "report_id": "c92d5081-12ca-4643-ae79-0a3bce47136b",
  "tenant_ref": "tenant:acme",
  "submitter_ref": "subject:52f9312a",
  "items": [{
    "line_id": "20542eb2-d893-4f1b-81fc-1bf47ad2e2ac",
    "expense_date": "2026-07-01",
    "category_code": "TRAVEL",
    "subcategory_code": "AIRFARE",
    "vendor_code": "AIRLINE_A",
    "amount": "430.00",
    "currency": "USD",
    "receipt": {"attached": true, "digest": "sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"}
  }],
  "policy": {
    "policy_version_ref": "travel-v2",
    "rules": [{
      "rule_ref": "travel-airfare-v2",
      "category_code": "TRAVEL",
      "max_per_item": "500.00",
      "receipt_required_at_or_above": "25.00"
    }]
  }
}
```

The service defensively redacts common email, phone, payment-number, URL, and
government-ID patterns from the optional `description_excerpt` and from human
remarks before persistence. Those fields should still be omitted unless they
are needed for deterministic review.

Every `ReviewResult` includes:

```json
{
  "human_review": {
    "required": true,
    "automated_action_taken": false,
    "allowed_actions": ["approve", "reject", "send_back", "acknowledge", "override_recommendation"]
  }
}
```

`POST /v1/review-jobs/{id}/dispositions` appends an auditable human verdict.
The core workflow must independently validate the reviewer's permission and
perform any status change; this service merely records the advisory context.

## Run locally

```bash
cd ai_review_service
uv sync
uv run pytest
AI_REVIEW_DATABASE_PATH=var/ai-review.sqlite3 uv run uvicorn ai_review_service.api:create_app --factory --port 8011
```

Queued jobs are processed automatically by a bounded local background worker;
the core API only needs to publish `POST /v1/review-jobs` and never needs an
inline processing switch. The local worker retries only up to the job's
configured attempt budget, and it resumes queued/interrupted work when this
single-process SQLite service restarts. For the SQLite default, run one AI
service process per database file. Use an AI-service-owned queue/repository
when scaling to multiple workers.

Useful local settings are:

```bash
AI_REVIEW_AUTO_PROCESS_JOBS=true
AI_REVIEW_LOCAL_WORKER_MAX_CONCURRENCY=1
AI_REVIEW_LOCAL_WORKER_RETRY_DELAY_SECONDS=0.25
AI_REVIEW_JOB_MAX_ATTEMPTS=3
```

The default `AI_REVIEW_PROVIDER=rule_based` makes no model request. Select one
optional provider and configure it only in the isolated AI-service deployment.
Never commit a vendor key: use an ignored local `.env` for development and a
secret manager or runtime secret injection in deployed environments.

Gemini:

```bash
uv sync --extra gemini
AI_REVIEW_PROVIDER=gemini AI_REVIEW_GEMINI_API_KEY=<secret> AI_REVIEW_GEMINI_MODEL=gemini-2.5-flash \
  uv run uvicorn ai_review_service.api:create_app --factory --port 8011
```

Groq uses its official Python SDK and JSON Object Mode. The default model is
`openai/gpt-oss-20b`; set `AI_REVIEW_GROQ_MODEL` explicitly if a project-level
model allow-list requires another supported JSON-capable model.

```bash
uv sync --extra groq
AI_REVIEW_PROVIDER=groq AI_REVIEW_GROQ_API_KEY=<secret> AI_REVIEW_GROQ_MODEL=openai/gpt-oss-20b \
  uv run uvicorn ai_review_service.api:create_app --factory --port 8011
```

The HTTP API is intended for an internal event gateway/worker, not browsers or
the public internet. Set `AI_REVIEW_SERVICE_TOKEN` in every non-local
deployment. When configured, **every** `/v1` operation requires an exact
service-to-service bearer token:

```bash
curl -H "Authorization: Bearer $AI_REVIEW_SERVICE_TOKEN" \
  http://localhost:8011/v1/review-jobs/<job-id>
```

The included `/process` endpoint remains an authenticated operator/recovery
hook. Production deployments may replace the local worker with an
AI-service-owned queue consumer that calls the same
`ExpenseReviewService.process(job_id)` method; it must keep the AI datastore
separate from the reimbursement database.

## Tests

The focused suite covers deterministic findings, PII redaction and provider
minimization, retry/timeout fallback, automatic local processing, recovery of
interrupted work, optional bearer authentication, idempotent separate
persistence, human dispositions, and the private job API.
