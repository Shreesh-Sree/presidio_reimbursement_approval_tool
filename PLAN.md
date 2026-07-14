# Enterprise Expense Reimbursement Approval System — Implementation Plan (F1–F8)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan phase-by-phase, task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Execute one phase at a time; each phase ends with working, testable software.

**Goal:** Build the full reimbursement approval platform (F1–F8) — RBAC user management, versioned policies, multi-line expense reports, receipt/policy-doc uploads, policy validation, multi-level approval workflow, and status tracking with notifications — on the planned `database/schema.dbml` foundation.

**Architecture:** Rebuild the backend as a layered FastAPI app (Postgres + SQLAlchemy 2.0 + Alembic) mirroring `database/schema.dbml`: UUID PKs, soft-delete + optimistic-lock mixins, RBAC via `roles`/`permissions`/`user_roles`/`role_permissions`, and thin routers over a `services/` business layer. Rebuild the frontend as a React 19 SPA (react-router + TanStack Query + shadcn/ui) with an auth context and feature modules per F-area. File storage uses S3 (boto3) behind a `StorageBackend`; email uses real SMTP behind an `EmailSender` interface. The existing `agent.py` AI audit is preserved and re-wired to the new models.

**Tech Stack:** Python 3.14, FastAPI, SQLAlchemy 2.0, PostgreSQL 16, Alembic, pyjwt, passlib[bcrypt], boto3, aiosmtplib, google-genai. React 19, Vite, TypeScript, react-router, @tanstack/react-query, axios, shadcn/ui (Tailwind + Radix), vitest.

---

## Context

Why this rebuild: the repo currently has a **simple SQLite** backend (Integer PKs, a single `role` string column, no user deactivation, no admin user-management endpoints, no RBAC) and a **bare Vite boilerplate** frontend. `database/schema.dbml` describes a far richer intended design (25+ tables, UUID PKs, RBAC, soft-delete, versioning, workflow rules, approvals, notifications, audit). The product spec (F1–F8) requires capabilities the current code cannot express — most immediately **multi-role users** ("a user can be both Employee and Approver"), **admin user lifecycle**, **versioned policies that don't retroactively change approved claims**, and a **multi-level approval workflow**.

Decision (confirmed with product owner): rebuild the backend against the DBML, model multi-role via a `user_roles` join table, deliver **in-app + real SMTP** notifications, and store files in **S3**. Outcome: a production-shaped, testable platform covering all eight feature areas, executed in phases where each phase is independently shippable.

**Existing code to preserve/adapt (do not discard blindly):**
- `backend/agent.py` — AI expense audit (rule-based + Gemini). Re-wire to new models in Phase 6.
- Password/JWT logic in `backend/auth.py` — port into `app/core/security.py`.
- Working request/response shapes in `backend/schemas.py` — reference when writing new Pydantic schemas.

**Schema extensions beyond `database/schema.dbml`** (the DBML under-specifies F2 policy versioning; these tables are added and the DBML file is updated to match in Phase 3):
- `policies` (name, version_label, is_active, effective_from, uploaded_document_attachment_id) — versioned policy header.
- `policy_rules` (policy_id, category_id, vendor_id, max_per_day, max_per_trip, per_category_cap, receipt_required_above) — structured constraints.
- `expense_reports.applied_policy_id` — snapshot the active policy at submission so later policy edits never mutate submitted/approved claims (F2 requirement).

---

## Global Constraints

- **DB**: PostgreSQL only. UUID PKs (`server_default=text("gen_random_uuid()")`). `decimal(18,2)` for money; `base_currency` default `'INR'` on organization.
- **Every table** carries the DBML common columns via mixins: `created_at`, `updated_at`, `deleted_at`, `is_deleted` (default false), `version` (integer, used as SQLAlchemy `version_id_col` for optimistic locking). All reads filter `is_deleted = false`; deletes are soft.
- **Multi-tenant-ready single company**: every domain query is scoped by `organization_id`. Uniqueness is per-org where the DBML says so (e.g. `(organization_id, email)`).
- **RBAC**: authorization is permission-based (`permissions.code` like `user:create`, `report:approve`). Roles bundle permissions via `role_permissions`. A user holds ≥1 role via `user_roles`. System roles: `administrator`, `approver`, `employee` (a user may hold `employee` + `approver`).
- **Auth**: JWT bearer + persisted `sessions` (store `session_token_hash`, `expires_at`, `revoked_at`). Login is denied for `user_status != active`. Logout revokes the session.
- **Audit**: every insert/update/delete on domain tables writes an `audit_logs` row (`before_json`/`after_json`, `performed_by`) via a service hook.
- **Secrets via env** (pydantic-settings, never hardcoded): `DATABASE_URL`, `JWT_SECRET`, `SMTP_HOST/PORT/USER/PASSWORD/FROM`, `AWS_REGION`, `S3_BUCKET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `GEMINI_API_KEY`.
- **Testing**: pytest against a real Postgres (testcontainers), function-scoped transaction rollback per test. S3 mocked with `moto`; `EmailSender` and AI agent mocked via interface. TDD: failing test first, minimal impl, commit per logical change. Conventional commits (`feat|fix|refactor|test|chore`). Never push `main`.
- **Frontend**: strict TS. Server state via TanStack Query only (no ad-hoc fetch-in-effect). Forms accessible (shadcn + Radix). vitest + React Testing Library. `prettier`/`eslint` clean.

---

## Target File Structure

```
backend/
  app/
    main.py                     # FastAPI app: middleware, router registration, startup
    core/
      config.py                 # pydantic-settings Settings
      database.py               # engine, SessionLocal, Base, get_db
      security.py               # hash/verify, JWT create/decode  (port auth.py)
      deps.py                   # get_current_user, require_permission(...)
      storage.py                # StorageBackend + S3Backend (boto3)
      email.py                  # EmailSender + SmtpEmailSender (aiosmtplib)
      errors.py                 # typed HTTPException helpers
    models/
      base.py                   # UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin
      __init__.py               # import all models for Alembic metadata
      organization.py department.py user.py role.py permission.py
      user_role.py role_permission.py project.py expense_category.py vendor.py
      policy.py policy_rule.py                     # schema extension (F2)
      expense_report.py expense_item.py attachment.py
      workflow_rule.py approval_level.py approval_history.py
      delegation.py bank_detail.py payment_record.py notification.py
      comment.py tag.py report_tag.py session.py audit_log.py setting.py
    schemas/                    # Pydantic v2, one module per domain
    services/                   # business logic, one module per domain area
      audit_service.py user_service.py org_chart_service.py policy_service.py
      category_service.py report_service.py item_service.py attachment_service.py
      validation_service.py workflow_service.py approval_service.py
      notification_service.py comment_service.py
    api/routes/                 # thin routers, one per feature
      auth.py users.py roles.py org_chart.py policies.py categories.py vendors.py
      reports.py items.py attachments.py approvals.py notifications.py comments.py
    agent.py                    # ported AI audit (re-wired to new models)
  alembic/                      # migrations (env.py targets app.models Base.metadata)
  tests/
    conftest.py                 # testcontainers postgres, db session, client, factories
    factories.py                # model factories (org, user, role, report, ...)
    <one test module per service/route>
  pyproject.toml                # add: psycopg[binary], boto3, aiosmtplib, testcontainers, moto, pytest, httpx, factory-boy
  docker-compose.yml            # postgres + mailhog + localstack (dev)

frontend/
  src/
    main.tsx                    # QueryClientProvider + RouterProvider
    routes.tsx                  # route tree
    lib/api.ts                  # axios instance + auth interceptor
    lib/queryClient.ts
    auth/AuthContext.tsx auth/useAuth.ts auth/ProtectedRoute.tsx
    components/ui/              # shadcn generated components
    components/AppLayout.tsx    # nav shell, role-aware menu
    features/auth/LoginPage.tsx
    features/users/            # UsersPage, UserForm, RoleMultiSelect, ManagerSelect
    features/org-chart/OrgChartPage.tsx
    features/policies/         # PoliciesPage, PolicyForm, PolicyUpload, RuleEditor
    features/categories/CategoriesPage.tsx
    features/reports/          # ReportsListPage, ReportEditor, LineItemRow, ReceiptUpload
    features/approvals/        # ApprovalQueuePage, ReportReview, ActionBar
    features/notifications/    # NotificationBell, NotificationFeed
    types/                     # shared TS types mirroring API schemas
  tailwind.config.ts components.json  # shadcn setup
```

---

## Phase Plan (each phase = shippable increment)

| Phase | Delivers | Feature |
|-------|----------|---------|
| 0 | Postgres, config, base mixins, Alembic baseline, test harness, seed | infra |
| 1 | Auth + RBAC (login/session/permissions), audit hook | infra/F1 |
| 2 | User CRUD, deactivate, manager assignment, multi-role, org chart + UI | **F1** |
| 3 | Categories/vendors, versioned policies, policy-doc upload (S3) + UI | **F2** |
| 4 | Expense reports (draft/submit/withdraw), line items, running total + UI | **F3, F4** |
| 5 | Receipt uploads (S3) + validation/flagging + UI | **F5** |
| 6 | Policy validation engine + violation flags + AI audit re-wire + UI | **F6** |
| 7 | Multi-level approval workflow (approve/reject/send-back, routing) + UI | **F7** |
| 8 | Status tracking, notifications (in-app + SMTP), comments + UI | **F8** |

> Phases 1→8 depend on 0. Phases 4→8 depend on 2 and 3. Within a phase, backend tasks precede their frontend task.

---

## Phase 0 — Foundation & Infra

### Task 0.1: Project config + settings
**Files:** Create `backend/app/core/config.py`; modify `backend/pyproject.toml`; Create `backend/docker-compose.yml`, `backend/.env.example`; Test `backend/tests/test_config.py`.

**Interfaces — Produces:** `Settings` (pydantic-settings) with typed fields for all Global-Constraints env vars; a cached `get_settings()`.

- [ ] **Step 1: Add deps to `pyproject.toml`** — under `dependencies`: `psycopg[binary]>=3.2`, `boto3>=1.35`, `aiosmtplib>=3.0`, `pydantic-settings>=2.5`. Add a `[dependency-groups] dev` with `pytest`, `pytest-asyncio`, `httpx`, `testcontainers[postgres]`, `moto[s3]`, `factory-boy`.
- [ ] **Step 2: Write failing test** `test_config.py`: set env `DATABASE_URL`, `JWT_SECRET`, `S3_BUCKET`; assert `get_settings().database_url` and `.s3_bucket` read them and that missing `JWT_SECRET` raises.
- [ ] **Step 3: Run test, verify fails** — `uv run pytest backend/tests/test_config.py -v` → import error / no module.
- [ ] **Step 4: Implement `config.py`**

```python
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "no-reply@presidio.com"
    aws_region: str = "us-east-1"
    s3_bucket: str
    gemini_api_key: str | None = None

@lru_cache
def get_settings() -> Settings:
    return Settings()  # raises on missing required fields — fail loud
```

- [ ] **Step 5: Run test, verify passes.**
- [ ] **Step 6: Write `docker-compose.yml`** (postgres 16, mailhog for dev SMTP, localstack s3) and `.env.example`. Commit: `chore: add settings, dev deps, docker-compose`.

### Task 0.2: Database + base model mixins
**Files:** Create `backend/app/core/database.py`, `backend/app/models/base.py`, `backend/app/models/__init__.py`; Test `backend/tests/test_base_model.py`.

**Interfaces — Produces:** `Base`, `get_db()`; mixins `UUIDMixin`, `TimestampMixin`, `SoftDeleteMixin`, `VersionMixin`. All models inherit `Base` + the four mixins.

- [ ] **Step 1: Failing test** — define a throwaway model using the mixins; assert an inserted row gets a UUID `id`, `is_deleted is False`, `version == 1`, and non-null timestamps.
- [ ] **Step 2: Run, verify fails.**
- [ ] **Step 3: Implement `database.py`** (engine from `get_settings().database_url`, `SessionLocal`, `Base = declarative_base()`, `get_db()` generator) **and `base.py`:**

```python
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("now()"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("now()"), onupdate=datetime.utcnow, nullable=False)

class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

class VersionMixin:
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    __mapper_args__ = {"version_id_col": None}  # set per-model to the version column
```

- [ ] **Step 4: Run, verify passes.**
- [ ] **Step 5: Commit** `feat: add base model mixins and database session`.

### Task 0.3: All SQLAlchemy models mirroring the DBML
**Files:** Create one module per table under `backend/app/models/` (see structure); register all in `models/__init__.py`. Test `backend/tests/test_models_metadata.py`.

**Interfaces — Produces:** every ORM model named in `database/schema.dbml` plus the Phase-3 extension models (`Policy`, `PolicyRule`) and `ExpenseReport.applied_policy_id`. Enums map to Postgres enums or `String` + `CheckConstraint`.

- [ ] **Step 1: Failing test** — `Base.metadata.tables` contains every expected table name (assert against a hardcoded set covering the DBML) and key FKs resolve (e.g. `users.manager_user_id -> users.id`).
- [ ] **Step 2–N (per model, TDD-batched):** implement each model as a small module following the `base.py` mixins and the exact columns/indexes/refs from `database/schema.dbml`. **Pattern (canonical example — `user.py`):**

```python
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin

class User(UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base):
    __tablename__ = "users"
    organization_id: Mapped[...] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    department_id: Mapped[...] = mapped_column(ForeignKey("departments.id"), nullable=False)
    manager_user_id: Mapped[...] = mapped_column(ForeignKey("users.id"), nullable=True)
    employee_number: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str]
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    manager = relationship("User", remote_side="User.id")
    roles = relationship("Role", secondary="user_roles", viewonly=True)
    __mapper_args__ = {"version_id_col": VersionMixin.version}
    # indexes per DBML: (organization_id, email) unique, etc.
```

Repeat this pattern for all remaining tables, copying columns/enums/indexes verbatim from the DBML. Keep each model module focused.
- [ ] **Final step: Run metadata test, verify passes. Commit** `feat: add full ORM model set mirroring schema.dbml`.

### Task 0.4: Alembic baseline migration
**Files:** Create `backend/alembic/` (via `alembic init`), configure `alembic/env.py` to import `app.models` metadata and read `DATABASE_URL`; generate `alembic/versions/0001_baseline.py`. Test `backend/tests/test_migrations.py`.

- [ ] **Step 1:** `alembic init alembic`; point `env.py` `target_metadata = Base.metadata`; enable the `pgcrypto` requirement — first migration op: `op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")`.
- [ ] **Step 2: Failing test** — spin a fresh Postgres (testcontainers), run `alembic upgrade head`, assert all tables exist and `alembic downgrade base` is clean.
- [ ] **Step 3:** `alembic revision --autogenerate -m baseline`; review the generated diff against the DBML (indexes, uniques, FKs). Fix drift.
- [ ] **Step 4: Run test, verify passes. Commit** `feat: add alembic baseline migration`.

### Task 0.5: Test harness + factories + seed
**Files:** Create `backend/tests/conftest.py`, `backend/tests/factories.py`, `backend/app/seed.py`. Test `backend/tests/test_seed.py`.

**Interfaces — Produces:** pytest fixtures `db` (session, rolled back per test), `client` (FastAPI `TestClient` with `get_db` overridden), `auth_client(user)`; factories for core models. `seed_db(db)` creates the organization, a department, system roles + permissions + `role_permissions`, and a bootstrap administrator.

- [ ] **Step 1:** implement `conftest.py`: session-scoped testcontainers Postgres, `alembic upgrade head` once, function-scoped nested-transaction rollback.
- [ ] **Step 2: Failing test** `test_seed.py` — after `seed_db`, assert roles `{administrator, approver, employee}` exist, admin user has `administrator` role via `user_roles`, and permissions are attached.
- [ ] **Step 3:** implement `seed.py` (idempotent). Permissions to seed (codes): `user:{create,read,update,deactivate}`, `role:assign`, `policy:{manage,read}`, `category:manage`, `report:{create,read,submit,withdraw}`, `item:manage`, `attachment:{upload,read}`, `report:approve`, `notification:read`.
- [ ] **Step 4: Run, verify passes. Commit** `feat: add test harness, factories, and idempotent seed`.

---

## Phase 1 — Auth & RBAC

### Task 1.1: Security primitives
**Files:** Create `backend/app/core/security.py` (port from `backend/auth.py`); Test `backend/tests/test_security.py`.
**Interfaces — Produces:** `hash_password`, `verify_password`, `create_access_token(subject, extra_claims)`, `decode_access_token`, `hash_session_token`.
- [ ] TDD: test round-trip hash/verify, token encode/decode, expiry rejection → implement using `passlib[bcrypt]` + `pyjwt` reading `get_settings()` → commit `feat: add security primitives`.

### Task 1.2: Audit service
**Files:** Create `backend/app/services/audit_service.py`; Test `test_audit_service.py`.
**Interfaces — Produces:** `record_audit(db, entity_name, record_id, operation, before, after, performed_by, request_meta)` writing an `audit_logs` row. Consumed by every mutating service.
- [ ] TDD: assert a mutation writes one audit row with correct `before_json`/`after_json` → implement → commit.

### Task 1.3: Auth dependencies (RBAC gate)
**Files:** Create `backend/app/core/deps.py`; Test `test_deps.py`.
**Interfaces — Produces:** `get_current_user(token, db)` (validates JWT + non-revoked session + `status == active`); `require_permission(code) -> dependency` that 403s when the user's roles don't grant `code`. **Consumed by every protected route.**
- [ ] **Failing test:** a route guarded by `require_permission("user:create")` returns 403 for an employee, 200 for admin.
- [ ] **Implement** `deps.py`:

```python
def require_permission(code: str):
    def _dep(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        if not user_has_permission(db, user, code):
            raise HTTPException(status_code=403, detail=f"Missing permission: {code}")
        return user
    return _dep
```

- [ ] Run, verify, commit `feat: add RBAC permission dependency`.

### Task 1.4: Auth routes (login/logout/me)
**Files:** Create `backend/app/api/routes/auth.py`, `backend/app/schemas/auth.py`; wire router in `app/main.py`. Test `test_auth_routes.py`.
**Interfaces — Produces:** `POST /api/auth/login` (validates creds + active status, creates a `sessions` row, returns JWT), `POST /api/auth/logout` (revokes session), `GET /api/auth/me`.
- [ ] **Failing tests:** login with seeded admin → 200 + token; login for `status=inactive` → 401; `/me` with token → user + roles; logout → subsequent `/me` 401.
- [ ] Implement routes + `app/main.py` (FastAPI app, CORS from settings, include routers, startup runs `seed_db`). Commit `feat: add auth login/logout/me with sessions`.

---

## Phase 2 — F1: User & Role Management  *(canonical vertical slice — later features follow this shape)*

### Task 2.1: User service (CRUD + deactivate)
**Files:** Create `backend/app/services/user_service.py`, `backend/app/schemas/user.py`; Test `test_user_service.py`.
**Interfaces — Produces:** `create_user`, `update_user`, `deactivate_user` (sets `status='inactive'`, keeps row — soft, not delete), `list_users(org_id, filters)`, `get_user`. All call `record_audit`. `create_user` hashes password, enforces `(organization_id, email)` uniqueness, requires ≥1 valid role.
- [ ] **Failing tests:** create persists + audits; duplicate email → error; deactivate flips status and blocks future login (assert via login route); update changes `full_name`/`designation`.
- [ ] Implement service. Commit `feat: add user service with deactivate`.

### Task 2.2: Role assignment + multi-role
**Files:** Modify `user_service.py` (add `set_user_roles`); Create `backend/app/services/role_service.py`; Test `test_role_service.py`.
**Interfaces — Produces:** `set_user_roles(db, user, role_codes, actor)` reconciling `user_roles` rows (soft-delete removed, insert added); `list_roles`. Supports a user holding both `employee` and `approver`.
- [ ] **Failing test:** assign `[employee, approver]` → `user.roles` has both; re-assign `[employee]` → approver row soft-deleted; assigning unknown role → error.
- [ ] Implement. Commit `feat: add multi-role assignment`.

### Task 2.3: Manager assignment (cycle-safe)
**Files:** Modify `user_service.py` (`set_manager`); Test extend `test_user_service.py`.
**Interfaces — Produces:** `set_manager(db, user, manager_id, actor)` validating manager is in same org and that assignment introduces **no cycle** in the `manager_user_id` chain.
- [ ] **Failing tests:** set valid manager; self-manager → error; A→B then B→A cycle → error.
- [ ] Implement (walk up the chain to detect cycles). Commit `feat: add cycle-safe manager assignment`.

### Task 2.4: Org chart service
**Files:** Create `backend/app/services/org_chart_service.py`; Test `test_org_chart_service.py`.
**Interfaces — Produces:** `build_org_tree(db, org_id) -> list[OrgNode]` — nested tree from `manager_user_id`, roots = users with no manager (or department heads). Each node: `{id, full_name, designation, roles, department, reports: [...]}`.
- [ ] **Failing test:** seed CEO→manager→2 employees, assert tree depth/shape.
- [ ] Implement (single query + in-memory tree build; avoid N+1). Commit `feat: add org chart builder`.

### Task 2.5: User + roles + org-chart routes
**Files:** Create `backend/app/api/routes/users.py`, `roles.py`, `org_chart.py`; wire in `main.py`. Test `test_user_routes.py`.
**Interfaces — Produces:**
- `POST /api/users` `require_permission("user:create")`; `PATCH /api/users/{id}` (`user:update`); `POST /api/users/{id}/deactivate` (`user:deactivate`); `GET /api/users` (`user:read`); `GET /api/users/{id}`.
- `PUT /api/users/{id}/roles` (`role:assign`); `PUT /api/users/{id}/manager` (`user:update`); `GET /api/roles`.
- `GET /api/org-chart` (`user:read`).
- [ ] **Failing tests** per route incl. 403 matrix (employee blocked from create/assign). Implement thin routers delegating to services. Commit `feat: add user/role/org-chart routes`.

### Task 2.6: Frontend foundation (auth + layout + api client)
**Files:** Modify `frontend/package.json` (add `react-router-dom`, `@tanstack/react-query`, `axios`; init Tailwind + shadcn via `components.json`), `frontend/src/main.tsx`, `frontend/src/App.tsx`; Create `frontend/src/lib/api.ts`, `lib/queryClient.ts`, `auth/AuthContext.tsx`, `auth/useAuth.ts`, `auth/ProtectedRoute.tsx`, `components/AppLayout.tsx`, `features/auth/LoginPage.tsx`, `src/routes.tsx`. Test `frontend/src/auth/__tests__/AuthContext.test.tsx`.
**Interfaces — Produces:** `api` axios instance (base URL from `VITE_API_URL`, bearer interceptor pulling token from `AuthContext`, 401→logout); `useAuth()` → `{user, permissions, login, logout}`; `<ProtectedRoute requires="perm" />`; role-aware `<AppLayout>`.
- [ ] **Failing test:** rendering a `ProtectedRoute` without auth redirects to `/login`; with a permission-lacking user hides the guarded link.
- [ ] Implement provider tree in `main.tsx` (`QueryClientProvider` → `AuthProvider` → `RouterProvider`), login page (posts `/api/auth/login`, stores token, fetches `/me`). Commit `feat(fe): auth context, api client, app layout, login`.

### Task 2.7: Users admin UI + org chart UI
**Files:** Create `features/users/UsersPage.tsx`, `UserForm.tsx`, `RoleMultiSelect.tsx`, `ManagerSelect.tsx`, `features/users/api.ts` (query hooks); `features/org-chart/OrgChartPage.tsx`, `features/org-chart/api.ts`; add routes. Test `features/users/__tests__/UsersPage.test.tsx`.
**Interfaces — Consumes:** `/api/users`, `/api/users/{id}/roles`, `/api/users/{id}/manager`, `/api/roles`, `/api/org-chart`.
- [ ] **Failing test:** UsersPage lists users (mocked query), opening the form and submitting calls create mutation; deactivate button calls deactivate endpoint. Role multi-select allows Employee+Approver together.
- [ ] Implement with TanStack Query hooks + shadcn `Table`/`Dialog`/`Form`/`Select`. Org chart: recursive tree component from `/api/org-chart`. Commit `feat(fe): admin user management + org chart`.

**Phase 2 exit:** admin can log in, create/update/deactivate users, assign multiple roles + a manager, and view the org chart. **F1 complete.**

---

## Phase 3 — F2: Policy Document & Rule Management

### Task 3.1: Update DBML + migration for policy tables
**Files:** Modify `database/schema.dbml` (add `policies`, `policy_rules`, `expense_reports.applied_policy_id`); Create models `app/models/policy.py`, `policy_rule.py`; Alembic `0002_policies.py`. Test `test_migrations.py` (extend).
- [ ] Add tables per the **Schema extensions** note in Context. Autogenerate + review migration. TDD upgrade/downgrade. Commit `feat: add policy + policy_rule schema`.

### Task 3.2: Category & vendor services + routes
**Files:** Create `services/category_service.py`, `api/routes/categories.py`, `api/routes/vendors.py`, schemas. Tests per service/route.
**Interfaces — Produces:** category CRUD supporting hierarchy (`parent_category_id`, so Travel → Airfare/Taxi/Hotel), `receipt_required`, `max_amount`; vendor CRUD. Guarded by `category:manage`.
- [ ] TDD create/list/hierarchy; routes with 403 matrix. Commit `feat: category and vendor management`.

### Task 3.3: Policy service (versioning + active flag + doc upload)
**Files:** Create `services/policy_service.py`, `services/attachment_service.py`, `api/routes/policies.py`, schemas. Uses `core/storage.py`. Tests with `moto` S3.
**Interfaces — Produces:**
- `StorageBackend`/`S3Backend` (`put(key, bytes, content_type) -> storage_path`, `get`, validate mime/size). `attachment_service.upload(entity_type, entity_id, file, actor)` computes checksum, stores to S3, writes `attachments` row.
- `policy_service`: `create_policy_version(name, version_label, rules, doc_file)`, `activate_policy(id)` (deactivates prior active), `get_active_policy`, `list_policies`. Only one active policy at a time. Editing an inactive/new version never touches `expense_reports.applied_policy_id` of existing reports.
- [ ] **Failing tests:** upload PDF → attachment row + S3 object (moto); creating v2 and activating flips `is_active`; active-policy lookup returns latest active; validates file type/size.
- [ ] Implement. Commit `feat: versioned policies with S3 document upload`.

### Task 3.4: Policy management UI
**Files:** `features/policies/PoliciesPage.tsx`, `PolicyForm.tsx`, `PolicyUpload.tsx`, `RuleEditor.tsx`, `features/categories/CategoriesPage.tsx`, feature `api.ts`. Tests.
**Interfaces — Consumes:** `/api/policies`, `/api/policies/{id}/activate`, `/api/policies/upload-doc`, `/api/categories`, `/api/vendors`.
- [ ] TDD list/create/activate/upload; rule editor for category/vendor caps (`max_per_day`, `max_per_trip`, `per_category_cap`, `receipt_required_above`). Commit `feat(fe): policy and category management`.

**Phase 3 exit:** admin manages categories/vendors, uploads versioned policy docs, edits structured rules, marks an active version. **F2 complete.**

---

## Phase 4 — F3 & F4: Expense Reports + Line Items

### Task 4.1: Report service (draft/submit/withdraw lifecycle)
**Files:** `services/report_service.py`, `schemas/report.py`, `api/routes/reports.py`. Tests.
**Interfaces — Produces:** `create_report` (status `draft`, generates `report_number`), `update_report` (only in `draft`/sent-back), `submit_report` (draft→submitted, snapshots `applied_policy_id` = active policy, sets `submitted_at`, triggers Phase 7 workflow init), `withdraw_report` (submitted→draft while not yet acted on), `list_reports` (scoped: employee sees own; approver sees queue+own; admin all — port logic from old `main.py`), running `total_amount` recompute.
- [ ] **Failing tests:** draft create; edit blocked once `submitted`; submit sets snapshot + timestamp; withdraw returns to draft; report_number unique.
- [ ] Implement. Commit `feat: expense report lifecycle`.

### Task 4.2: Line-item service + running total
**Files:** `services/item_service.py`, `schemas/item.py`, `api/routes/items.py`. Tests.
**Interfaces — Produces:** `add_item`/`update_item`/`delete_item` (soft) — captures vendor, expense_date, category/sub-category, amount, currency, description, receipt (attachment link); enforce edits only pre-submission; recompute report `total_amount` on any change. Sequential `line_number` per report.
- [ ] **Failing tests:** add 3 items → report total = sum; delete item → total updates; edit after submit → error.
- [ ] Implement. Commit `feat: expense line items with running total`.

### Task 4.3: Reports UI (list + editor + line items)
**Files:** `features/reports/ReportsListPage.tsx`, `ReportEditor.tsx`, `LineItemRow.tsx`, `features/reports/api.ts`. Tests.
**Interfaces — Consumes:** `/api/reports`, `/api/reports/{id}/items`, `/api/reports/{id}/submit`, `/api/reports/{id}/withdraw`.
- [ ] TDD: create draft, add/edit/delete rows with live total, save draft vs submit, withdraw. Commit `feat(fe): report editor with line items`.

**Phase 4 exit:** employee creates/drafts/edits/submits/withdraws reports with multiple line items and a live total. **F3, F4 complete.**

---

## Phase 5 — F5: Receipt Uploads

### Task 5.1: Receipt upload on line items
**Files:** `api/routes/attachments.py`, extend `item_service.py`, `services/attachment_service.py`. Tests (`moto`).
**Interfaces — Produces:** `POST /api/items/{id}/receipt` (validate image/PDF, size limit, store to S3, link attachment); `GET /api/attachments/{id}` (presigned download, guarded `attachment:read` — employee owner, approver in chain, admin). Flag (not block) items missing a receipt when `receipt_required`/`receipt_required_above` applies.
- [ ] **Failing tests:** upload valid receipt → linked; oversize/wrong-type → 400; missing-receipt flag surfaces on the item; approver can download.
- [ ] Implement. Commit `feat: receipt uploads with validation and flagging`.

### Task 5.2: Receipt UI
**Files:** `features/reports/ReceiptUpload.tsx`, extend `LineItemRow.tsx`; approver-side view in Phase 7 UI. Tests.
- [ ] TDD upload control, missing-receipt badge, download link. Commit `feat(fe): receipt upload and view`.

**Phase 5 exit:** employees attach validated receipts; missing-receipt items are flagged; approvers/admin can view/download. **F5 complete.**

---

## Phase 6 — F6: Policy Validation

### Task 6.1: Validation engine
**Files:** `services/validation_service.py`. Tests.
**Interfaces — Produces:** `validate_item(db, item, policy)` and `validate_report(db, report)` — checks each item's category/sub-category + amount against the **snapshot** active policy's `policy_rules` (per-day, per-trip, per-category cap, receipt thresholds); sets `expense_items.is_policy_violated` + `policy_violation_reason`. Returns structured violations.
- [ ] **Failing tests:** taxi above cap → violated flag + reason; within cap → clean; per-category cap across items; missing-receipt-above-threshold flagged.
- [ ] Implement. Commit `feat: policy validation engine`.

### Task 6.2: Submit-time enforcement + justification
**Files:** extend `report_service.submit_report`, `schemas/report.py`. Tests.
**Interfaces — Produces:** on submit, run `validate_report`; **hard rule** — reports containing an amount/rule violation **cannot be submitted** (per spec's minimal-note choice: block, no override). Violations are persisted so approvers see the same flags (nothing hidden).
- [ ] **Failing tests:** submit with a violation → 422 listing violations; clean report → submits.
- [ ] Implement. Commit `feat: block submission of policy-violating reports`.

### Task 6.3: AI audit re-wire
**Files:** Modify `backend/app/agent.py` (port from existing `backend/agent.py`), call from `submit_report`, store on `approval_levels.ai_review` or a report field. Tests (mock genai).
- [ ] Adapt the existing rule-based + Gemini audit to new models; store audit JSON; graceful fallback when `GEMINI_API_KEY` unset. Commit `feat: re-wire AI expense audit to new models`.

### Task 6.4: Validation UI
**Files:** extend `ReportEditor.tsx` (inline violation warnings at submit), approver review shows same flags. Tests.
- [ ] TDD: violation banner blocks submit; flags visible. Commit `feat(fe): policy violation warnings`.

**Phase 6 exit:** items validated against the snapshot policy; violating reports blocked at submit; flags persisted and visible to approvers; AI audit attached. **F6 complete.**

---

## Phase 7 — F7: Multi-level Approval Workflow

### Task 7.1: Workflow init + approval service
**Files:** `services/workflow_service.py`, `services/approval_service.py`, `schemas/approval.py`, `api/routes/approvals.py`. Tests.
**Interfaces — Produces:**
- `workflow_service.init_workflow(report)` — on submit, create `approval_levels` level 1 = submitter's direct manager (`manager_user_id`). Optional amount-threshold rule (from `workflow_rules`/`settings`): reports above a configured total route to the next manager up after level-1 approval.
- `approval_service.act(report, approver, action, remarks)` where action ∈ `approve|reject|send_back`. Writes `approval_history`. **Reject** → report `rejected` (+ notify). **Send back** → status `sent_back` (employee may edit/resubmit). **Approve** → advance to next required level; when all levels approved → `approved` (pending payment). Enforce that only the current-level pending approver may act.
- Routes: `GET /api/approvals/queue` (`report:approve`), `POST /api/reports/{id}/action`.
- [ ] **Failing tests:** submit routes to direct manager; wrong approver acts → 403; reject sets rejected + history; send-back sets sent_back; approve at final level → approved; above-threshold escalates to next manager.
- [ ] Implement (port/replace old `main.py` action logic). Commit `feat: multi-level approval workflow`.

### Task 7.2: Approvals UI
**Files:** `features/approvals/ApprovalQueuePage.tsx`, `ReportReview.tsx`, `ActionBar.tsx`, `features/approvals/api.ts`. Tests.
**Interfaces — Consumes:** `/api/approvals/queue`, `/api/reports/{id}`, `/api/reports/{id}/action`.
- [ ] TDD: queue lists pending; review shows items + flags + receipts + AI audit; approve/reject/send-back with remarks. Commit `feat(fe): approval queue and review`.

**Phase 7 exit:** submitted reports route through the manager chain; approvers approve/reject/send-back; full approval moves report to Approved–Pending Payment. **F7 complete.**

---

## Phase 8 — F8: Status Tracking & Notifications

### Task 8.1: Email + notification services
**Files:** `core/email.py` (`EmailSender` + `SmtpEmailSender` via aiosmtplib), `services/notification_service.py`, `api/routes/notifications.py`, schemas. Tests (mock `EmailSender`; MailHog for manual).
**Interfaces — Produces:** `notify(db, recipient, template_code, payload, channels)` — writes a `notifications` row (in-app) and, for the `email` channel, sends via `EmailSender`; records `sent_at`/`status`. `GET /api/notifications` (feed), `POST /api/notifications/{id}/read`. Hook `notify` into every status change (submit, each approval action, final approval, rejection, send-back).
- [ ] **Failing tests:** status change creates a notification row + calls email sender; feed lists unread; mark-read sets `read_at`.
- [ ] Implement. Commit `feat: in-app + SMTP notifications on status change`.

### Task 8.2: Comments (approver↔employee clarification)
**Files:** `services/comment_service.py`, `api/routes/comments.py`, schemas. Tests.
**Interfaces — Produces:** threaded `comments` on a report with `visibility` (public/approvers_only), used for send-back clarification. `GET/POST /api/reports/{id}/comments`.
- [ ] TDD add/list/threading/visibility. Commit `feat: report comments`.

### Task 8.3: Status tracking + notifications UI
**Files:** `features/notifications/NotificationBell.tsx`, `NotificationFeed.tsx`; status timeline on `ReportReview.tsx`/report detail; comment thread component. Tests.
**Interfaces — Consumes:** `/api/notifications`, `/api/reports/{id}` (status + `approval_history`), `/api/reports/{id}/comments`.
- [ ] TDD: bell shows unread count (polling via TanStack Query), feed marks read, report detail shows real-time status + history + comments. Commit `feat(fe): status tracking, notifications, comments`.

**Phase 8 exit:** employees/approvers see real-time status per report and line item; notifications fire (in-app + email) on every status change; clarification via comments. **F8 complete.**

---

## Verification

**Per task:** run its pytest module (`uv run pytest backend/tests/test_x.py -v`) / vitest file; expect the failing→passing transition described. Never weaken a test to pass.

**Per phase (end-to-end, backend):** with `docker-compose up` (postgres + mailhog + localstack), run the full suite `uv run pytest backend/tests -v` and `alembic upgrade head` on a clean DB.

**Full-system smoke (after Phase 8):** start backend (`uv run uvicorn app.main:app`) + frontend (`npm run dev`), then drive the real flow in the browser (Playwright MCP or manual):
1. Log in as admin → create an approver-manager and an employee (employee also given approver role) → assign manager → view org chart.
2. As admin → create categories (Travel→Taxi), upload a policy doc, set a taxi cap, activate the policy.
3. As employee → create a report, add line items (one over the taxi cap), attach receipts → confirm submit is **blocked** by the violation → fix → submit.
4. As manager → open approval queue → review flags + receipts + AI audit → approve (verify escalation if above threshold) → confirm report reaches **Approved–Pending Payment**.
5. Verify in-app notifications appear at each step and emails land in MailHog; verify status timeline + comments on the report.

**Quality gates before each commit:** `uv run pytest` (touched area) green; frontend `npm run lint && npm run test` green; no hardcoded secrets; conventional commit message; one logical change.

---

## Self-Review Notes
- **Spec coverage:** F1→Phase 2, F2→Phase 3, F3/F4→Phase 4, F5→Phase 5, F6→Phase 6, F7→Phase 7, F8→Phase 8. Multi-role (Employee+Approver) → Task 2.2. "Policy changes don't alter approved claims" → `applied_policy_id` snapshot (Tasks 3.1/4.1/6.1). "Block submission on violation (no override)" → Task 6.2.
- **Type consistency:** `require_permission(code)` (1.3) used by all routers; `record_audit` (1.2) called by all mutating services; `StorageBackend`/`attachment_service.upload` (3.3) reused by receipts (5.1); `notify` (8.1) hooked by approval actions (7.1).
- **Scope note:** this is a large multi-subsystem build per explicit product-owner choice. Execute one phase per branch/review cycle; do not attempt all phases in one pass.
