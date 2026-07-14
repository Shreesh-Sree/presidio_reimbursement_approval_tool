# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status

Early scaffold stage. Current running code (`backend/`, `frontend/`) is a minimal MVP. `PLAN.md` describes a much larger planned rebuild (phases F1-F8: RBAC, Postgres, feature-module frontend) that is **not yet implemented**. Don't assume the planned structure below exists in code — check before referencing it.

## Commands

**Backend** (FastAPI, managed with `uv`, in `backend/`):
```
cd backend && uv run uvicorn main:app --reload
```
Docs: `http://127.0.0.1:8000/docs`. Health check: `/api/health`. No lint or test scripts defined yet.

**Frontend** (React 19 + TS + Vite, in `frontend/`):
```
npm run dev       # vite dev server
npm run build      # tsc -b && vite build
npm run lint       # oxlint
npm run preview
```
No test script yet.

## Architecture (current code)

Backend is a single-file FastAPI app, no layered structure yet:

- `backend/main.py` — all routes. Auth (`/api/auth/register|login|me|users`), policies (`/api/policies` CRUD, admin-only mutations + `/api/policies/upload-doc`), expenses (`/api/expenses` create/list/get/action, `/api/expenses/upload-receipt`). Receipts saved to `backend/static/receipts`, served at `/static`. CORS is wide open.
- `backend/auth.py` — JWT (pyjwt) + password hashing (bcrypt/passlib).
- `backend/models.py` — SQLAlchemy models: `User` (role: employee/approver/admin, self-referential `manager_id`), `Policy` (category limit + JSON rules), `ExpenseReport` (status: draft/submitted/pending_approval/approved/rejected/reimbursed), `ExpenseItem`, `ApprovalWorkflow` (per-report approver + status + AI review JSON field).
- `backend/agent.py` — expense audit logic, mixes rule-based checks with Gemini (`google-genai`) AI review.
- `backend/database.py` — SQLite at `database/reimbursements.db`, tables created via `Base.metadata.create_all` (no migrations yet).
- `backend/schemas.py` — Pydantic request/response schemas mirroring the models.
- `frontend/` — stock Vite React 19 + TypeScript scaffold. No routing, state management, or API client wired up yet.

## Planned rebuild (PLAN.md, database/schema.dbml — not yet implemented)

- Backend moving to layered `app/` structure (core/models/schemas/services/api/routes), Postgres (psycopg + alembic), UUID + soft-delete + version mixins matching `database/schema.dbml`, full RBAC (roles/permissions/user_roles/role_permissions tables), S3 (boto3) file storage, SMTP (aiosmtplib) email notifications.
- Frontend moving to react-router-dom + TanStack Query + axios + shadcn/ui, organized into feature modules under `src/features/{auth,users,org-chart,policies,categories,reports,approvals,notifications}`.
- Expense workflow: draft → submit → policy validation → multi-level approval → approved-pending-payment. Policies are versioned and snapshotted onto reports at submit time, so later policy edits don't retroactively affect already-submitted reports.
- Planned env vars: `DATABASE_URL`, `JWT_SECRET`, `SMTP_HOST/PORT/USER/PASSWORD/FROM`, `AWS_REGION`, `S3_BUCKET`, `AWS_ACCESS_KEY_ID/SECRET_ACCESS_KEY`, `GEMINI_API_KEY`.
- Full target schema: `database/schema.dbml`. Full phase breakdown: `PLAN.md`.
