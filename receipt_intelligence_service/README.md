# Receipt Intelligence Service

This is a separately deployable, deterministic receipt-analysis service. It is
intentionally independent from the reimbursement API, its ORM, and its
database. It never approves, rejects, routes, or updates an expense report.
The core application retains policy enforcement and every human workflow
decision.

## Boundary

~~~text
core reimbursement API -- async receipt-analysis event --> receipt service
                                                            |
                                               separate digest-only SQLite store
                                                            |
core API / approver UI <-- deterministic findings ----------+
~~~

The future core integration should dispatch a versioned metadata event after a
receipt is uploaded or an expense has no receipt. The service accepts only an
opaque organization scope, a SHA-256 digest, media type, byte count, policy
facts, and optionally caller-extracted plain text. It does not receive a raw
file, signed URL, filename, report ID, user identity, or core database
connection. Calling the endpoint from an asynchronous queue consumer preserves
the service boundary without persisting receipt content in a job queue.

## What it does

- validates supported PDF/image MIME types and a configurable file-size limit;
- detects a policy receipt-required threshold when no receipt is supplied;
- extracts bounded merchant, date, amount, and masked receipt-number candidates
  from supplied plain text in memory;
- detects duplicate SHA-256 receipt digests within one organization scope;
- detects prompt-injection or instruction-like text and excludes those lines
  from evidence extraction; and
- returns an explicit OCR disclosure.

This release runs explicit local Tesseract OCR for JPEG, PNG, and WebP receipts.
It receives image bytes only for the active advisory request and never persists them
or the extracted text. Install the `tesseract-ocr` system package on the service host.
The included Dockerfile installs that engine automatically.
PDF OCR remains intentionally unsupported. Any future OCR adapter must
be explicit, independently reviewed, and keep the same no-core-database
boundary. It makes no LLM, model-provider, web, or third-party API calls.

## Privacy and persistence

The SQLite store contains exactly:

- opaque organization scope;
- SHA-256 receipt digest;
- first/last seen timestamps; and
- a duplicate observation count.

It never stores supplied receipt text, extracted evidence, filenames, URLs,
report IDs, user IDs, raw file bytes, OCR output, or logs containing those
values. The service logger writes structured event names, correlation IDs,
status codes, finding counts, and duplicate booleans only.

The service rejects PostgreSQL URLs for its datastore so it cannot accidentally
reuse the core reimbursement database.

## Run locally

~~~bash
cd receipt_intelligence_service
uv sync
uv run pytest
export RECEIPT_INTELLIGENCE_SERVICE_TOKEN=local-dev-token
RECEIPT_INTELLIGENCE_DATABASE_PATH=var/receipt-intelligence.sqlite3 \
  uv run uvicorn receipt_intelligence_service.api:create_app --factory --port 8012
~~~

The `/health` and `/ready` probes do not expose receipt data. Every `/v1`
endpoint requires an exact bearer token; a missing service token makes private
operations unavailable rather than allowing anonymous access.

~~~bash
curl -X POST http://localhost:8012/v1/analyze \
  -H "Authorization: Bearer $RECEIPT_INTELLIGENCE_SERVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Request-ID: receipt-event-123" \
  -d '{
    "organization_scope": "org:opaque-123",
    "receipt": {
      "sha256_digest": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
      "media_type": "application/pdf",
      "size_bytes": 32000,
      "supplied_text": "Merchant: Metro Taxi\nTotal: USD 42.50",
      "text_source": "caller_extracted"
    },
    "policy": {
      "expense_amount": "42.50",
      "currency": "USD",
      "receipt_required_at_or_above": "25.00"
    }
  }'
~~~

## Configuration

All settings use the `RECEIPT_INTELLIGENCE_` prefix:

- `SERVICE_TOKEN` — required for private API calls;
- `DATABASE_PATH` — independent SQLite file, default
  `var/receipt-intelligence.sqlite3`;
- `MAX_FILE_BYTES` — default 10 MiB;
- `MAX_TEXT_CHARS` — default 24,000; and
- `ALLOWED_MEDIA_TYPES` — default PDF, JPEG, PNG, and WebP.

## Tests

~~~bash
cd receipt_intelligence_service
uv run pytest
~~~

The suite covers service-token denial, scoped digest deduplication, receipt
threshold findings, media/size guardrails, health/readiness, request
correlation, and prompt-injection detection with instruction-like text ignored.
