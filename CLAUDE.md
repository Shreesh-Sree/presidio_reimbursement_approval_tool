# CLAUDE.md

## Project state

This is an implemented, production-shaped reimbursement application — not the
old single-file MVP. The core workflow, RBAC, policy versioning, reports,
approvals, notifications, payments, delegations, analytics, CI, and Terraform
foundation are present. Check `git status` before editing: feature work may be
in progress. `PLAN.md` is historical planning material; do not treat it as the
source of truth or edit it unless a task explicitly asks for that.

The database migration chain is:

```text
001_baseline -> 002_add_policies -> 003_add_reports_workflow_and_collaboration
             -> 004_payment_operations -> 005_add_delegated_approval_audit
             -> 006_policy_tenant_scope
```

## Repository map

- `backend/app/` — layered FastAPI core:
  - `api/routes/` and request schemas expose typed, permission-protected APIs.
  - `models/` plus Alembic migrations own PostgreSQL persistence, UUIDs,
    soft-delete, and audit records.
  - `services/` own policy evaluation, report/approval workflow, notifications,
    storage, payments, delegations, analytics, and external-service clients.
  - `core/` contains settings, database/session lifecycle, JWT/RBAC dependencies,
    request correlation, and structured logging.
- `frontend/src/` — React 19 + TypeScript + Vite feature modules. React Router
  protects pages; TanStack Query and `lib/api.ts` are the only browser API
  access pattern. Features cover policies, categories, reports, approvals,
  notifications, delegations, payments, analytics, users, and workflows.
- `ai_review_service/` — separately deployable, advisory expense-review service
  with its own datastore.
- `receipt_intelligence_service/` — separate digest/metadata-only receipt
  analysis service with its own SQLite store.
- `policy_assistant_service/` — separate tenant/version-scoped, evidence-only
  policy RAG service with its own SQLite index.
- `deployment/` — cost-capped AWS Terraform and deployment guidance. Do not run
  `terraform apply` or deploy without explicit authorization.

## Local development

Use Node/npm and `uv`. The core API needs `backend/.env`; copy the example and
use a local PostgreSQL instance, Docker Compose, or an approved development
database. Never commit `.env`, credentials, generated SQLite files, or receipt
data.

```bash
# Core API
cd backend
docker compose up -d postgres       # optional local PostgreSQL
cp .env.example .env                # only if no local .env exists
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload

# Frontend, in another terminal
cd frontend
npm install
npm run dev
```

Core API docs are at `http://127.0.0.1:8000/docs`; health/readiness are
`/api/health` and `/api/ready`. `backend/main.py` remains a compatibility
entry point, but new work belongs under `backend/app/`.

Optional advisory services run independently; start only the one needed for a
task. Their README files are their authoritative local configuration guides.

```bash
cd ai_review_service && uv sync && uv run pytest -q
cd receipt_intelligence_service && uv sync && uv run pytest -q
cd policy_assistant_service && uv sync && uv run pytest -q
```

## Verification

Run the smallest relevant check while iterating, then the affected suite:

```bash
cd backend && uv run pytest tests -q
cd backend && uv run alembic check
cd frontend && npm run test && npm run lint && npm run build
cd ai_review_service && uv run pytest -q
cd receipt_intelligence_service && uv run pytest -q
cd policy_assistant_service && uv run pytest -q
```

GitHub Actions in `.github/workflows/ci.yml` runs backend tests/migration
checks, frontend lint/test/build, each advisory-service suite, Terraform
format/validation, and secret scanning on pull requests and `main` pushes.

## Frontend conventions

- Use `useQuery`/`useMutation` with typed functions in `frontend/src/lib/api.ts`;
  do not add ad-hoc `fetch` calls or hard-code API origins.
- Keep screens responsive and include loading, empty, error, keyboard, and
  permission states. Protect routes with `RequirePermission`.
- The visual system is Material UI with shadcn/Tailwind form primitives. The
  `ThemeModeProvider` supports persisted light, dark, and system modes; do not
  reintroduce OS-only dark-mode CSS or page-local theme state.
- Preserve the feature-based structure and write Vitest/Testing Library tests
  for user-visible behavior, not implementation internals.

## Core workflow and authorization

Reports move through draft/sent-back editing, submission with policy checks,
manager-chain review, `approved_pending_payment`, and finance settlement.
Policy snapshots prevent later edits from silently changing historical claims.
Use service-layer transactions and audit logging for workflow/state changes.
All API/UI access must be scoped by organization and `require_permission` / the
frontend permission guard; never infer access merely from a role label.

## AI and privacy boundaries

All AI-adjacent services are advisory-only and cannot approve, reject, route,
or pay a report.

- The core API sends `ai_review_service` a minimized, versioned event: opaque
  references, policy facts, aggregates, and receipt digests only. It must not
  send receipt bytes, OCR text, URLs, names, emails, descriptions, or database
  access. Provider output is cited, validated, and shown for human review.
- Receipt intelligence accepts only bounded metadata/digests and does not
  persist receipt content. Its manual report/item endpoint validates access and
  attachment linkage before it makes an optional HTTP call; keep it separate
  from the core ORM/database.
- The policy assistant retrieves only tenant/version-scoped policy evidence,
  returns citations, treats documents/questions as untrusted data, and makes
  no workflow decision. Its UI requires an administrator to explicitly paste
  approved text before indexing. External model access remains opt-in.

Preserve these contracts when adding integrations: use service tokens, opaque
IDs, least data, independent storage, and asynchronous/event-style handoffs.

## Change discipline

- Prefer focused conventional commits (`feat(fe): ...`, `fix(api): ...`).
- Add an Alembic migration for persistent-model changes; do not edit an applied
  migration or rely on `Base.metadata.create_all`.
- Keep payment data to report amounts and opaque processor references; never
  add bank-account fields to the core database, API, logs, exports, or UI.
- Treat Terraform, secrets, IAM, retention, and service deployment as separate
  reviewed changes. Follow `deployment/README.md` before infrastructure work.
