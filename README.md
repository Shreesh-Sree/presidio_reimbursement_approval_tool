# Presidio Reimbursement Approval Tool

A role-based expense and reimbursement system for Employees, Approvers, and
Administrators. It supports versioned policies, structured categories and
vendors, receipt uploads, policy validation, manager-chain approvals,
notifications, report comments, and an isolated AI expense-review service.

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
- An advisory-only `ai_review_service` with its own datastore. It receives a
  minimized policy/report snapshot, never mutates the reimbursement workflow,
  and requires a human decision.

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

## AI review service

The AI reviewer is deliberately a separate service and separate SQLite
datastore. It is optional for core reimbursement workflow operation.

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
```

Approvers see only the advisory summary, risk, findings, and the explicit
human-review gate. The AI service processes queued jobs automatically by
default; a provider timeout/failure cannot approve, reject, or block a core
workflow decision.

## Verification

```bash
cd backend && uv run pytest tests -q
cd backend && uv run alembic check
cd ../frontend && npm run test && npm run lint && npm run build
cd ../ai_review_service && uv run pytest -q
```

The backend migration chain is `001_baseline → 002_add_policies →
003_reports_workflow` and is checked against the SQLAlchemy metadata.
