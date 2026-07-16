# Presidio Reimbursement Approval Tool

A role-based expense and reimbursement system for Employees, Approvers, and
Administrators. It supports versioned policies, structured categories and
vendors, receipt uploads, policy validation, manager-chain approvals,
delegation/SLA handling, payment operations, analytics, notifications, report
comments, and isolated advisory services.

## What is included

- Employee reports with editable draft/sent-back states, multi-line items,
  live totals, receipts, and policy-violation explanations.
- Administrator policy versions, structured caps, category hierarchy, vendor
  constraints, document uploads, and activation without rewriting historical
  claims.
- RBAC with Employee/Approver/Administrator roles, a reporting hierarchy,
  user deactivation, and an organization chart.
- Sequential manager approvals, reject/send-back remarks, immutable approval
  history, reimbursement `approved_pending_payment` status, in-app alerts, and
  opt-in SMTP email delivery for status changes.
- Finance payment operations: a permission-protected queue, immutable payment
  events, currency-safe CSV/Excel/PDF export batches, and explicit paid/failed outcomes.
- Temporary approver delegation with cycle protection, preserved acting-for
  provenance, due dates, reminders, and idempotent SLA escalation.
- A custom React/Tailwind design system (no MUI), Radix dialogs/selects,
  Luma loading states, route-level error boundary, and an accessible aggregate
  reimbursement analytics dashboard.
- An advisory-only `ai_review_service` with its own datastore. It receives a
  minimized policy/report snapshot, never mutates the reimbursement workflow,
  and requires a human decision.
- A digest-only `receipt_intelligence_service` and a tenant/version-scoped
  `policy_assistant_service`. Both have independent SQLite stores and cannot
  access the reimbursement database or make workflow decisions.

## Run locally

Prerequisites: `uv`, Node/npm, and PostgreSQL (or the included Docker Compose
stack).

```bash
cd backend
docker compose up -d postgres
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`; interactive docs are at
`/docs`. `backend/main.py` is retained as a compatibility shim, so
`uv run uvicorn main:app --reload` serves the same application.

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL (normally `http://localhost:5173`). On a new deployment,
create the first administrator at `/bootstrap`; the bootstrap endpoint is
permanently disabled after the first active user exists.

## Isolated advisory services

The three services below are independently runnable and testable. The core API
uses narrow, authenticated HTTP clients for optional advisory calls; it never
imports their persistence packages or shares their databases. None can
approve, reject, route, or pay a report.

### AI expense review

The AI reviewer receives a minimized policy/report snapshot and is optional
for core reimbursement workflow operation.

```bash
cd ai_review_service
uv sync
AI_REVIEW_DATABASE_PATH=var/ai-review.sqlite3 \
  uv run uvicorn ai_review_service.api:create_app --factory --port 8011
```

Then set these in `backend/.env` and restart the API:

```dotenv
AI_REVIEW_SERVICE_URL=http://127.0.0.1:8011
# Set the same non-empty value in ai_review_service for service-to-service auth.
AI_REVIEW_SERVICE_TOKEN=
# Use a distinct long random value so opaque references survive token rotation.
AI_REVIEW_REFERENCE_HMAC_KEY=
```

Approvers see only the advisory summary, risk, findings, and the explicit
human-review gate. The AI service processes queued jobs automatically by
default; a provider timeout/failure cannot approve, reject, or block a core
workflow decision.

### Receipt intelligence

The receipt service accepts metadata only: an opaque organization scope,
SHA-256 digest, MIME type, byte size, policy facts, and optional
caller-extracted text. It stores only digest observations and returns
deterministic receipt/duplicate findings; it does not receive receipt bytes or
URLs.

```bash
cd receipt_intelligence_service
uv sync
export RECEIPT_INTELLIGENCE_SERVICE_TOKEN=replace-with-a-long-local-token
RECEIPT_INTELLIGENCE_DATABASE_PATH=var/receipt-intelligence.sqlite3 \
  uv run uvicorn receipt_intelligence_service.api:create_app --factory --port 8012
```

To enable the explicit manager review action, configure matching service URL
and token values in `backend/.env`, then restart the core API:

```dotenv
RECEIPT_INTELLIGENCE_SERVICE_URL=http://127.0.0.1:8012
RECEIPT_INTELLIGENCE_SERVICE_TOKEN=
```

Approvers can select **Check receipt metadata** for a line item. The core API
checks authorization and attachment linkage, then sends only opaque references,
checksum, MIME type, byte size, amount, currency, and frozen receipt-policy
threshold. The result is advisory and ephemeral; it never reads or sends the
receipt bytes, filename, link, OCR text, description, or employee data.

### Policy assistant

The policy assistant is an evidence-only RAG API. It chunks policy text in its
own tenant/version-scoped SQLite index and returns source citations. It uses a
deterministic local retriever by default; external provider calls are disabled
unless explicitly approved and configured.

```bash
cd policy_assistant_service
cp .env.example .env
uv sync
uv run uvicorn policy_assistant_service.api:create_app --factory --port 8013
```

To enable the policy-management panel, configure the service URL, matching
token, and a distinct stable reference key in `backend/.env`, then restart the
core API:

```dotenv
POLICY_ASSISTANT_SERVICE_URL=http://127.0.0.1:8013
POLICY_ASSISTANT_SERVICE_TOKEN=
POLICY_ASSISTANT_REFERENCE_HMAC_KEY=
```

Administrators explicitly paste approved policy text before indexing it, then
ask version-scoped questions and see cited evidence. Uploaded documents,
receipts, report data, and employee details are never automatically sent. The
Terraform runtime defines a private, separately credentialed container for the
service; it is not applied or deployed without explicit production approval.

## Verification

```bash
cd backend && uv run pytest tests -q
cd backend && uv run alembic check
cd ../frontend && npm run test && npm run lint && npm run build
cd ../ai_review_service && uv run pytest -q
cd ../receipt_intelligence_service && uv run pytest -q
cd ../policy_assistant_service && uv run pytest -q
```

The backend migration chain is `001_baseline → 002_add_policies →
003_reports_workflow → 004_payment_operations → 005_delegated_approvals →
006_policy_tenant_scope` and
is checked against the SQLAlchemy metadata.

Migration 006 never guesses a tenant for legacy policies: ambiguous historical
rows are placed in an inactive quarantine organization for controlled
reassignment or recreation before a tenant can use them.

## AWS deployment

The cost-capped AWS deployment lives in [deployment/](deployment/README.md).
It provisions the React SPA, FastAPI API, private PostgreSQL database, S3
uploads, three separately isolated advisory services, TLS/DNS, SES, monitoring,
and AWS Budgets with a USD 75/month guardrail. Terraform validates in CI but
does not apply infrastructure or deploy a runtime without explicit approval.
