# Presidio Reimbursement Approval Tool

Presidio is a role-based reimbursement workflow for employees, managers,
finance teams, and administrators. It provides expense-report submission,
multi-stage approval, payment operations, policy validation, receipt analysis,
and access-request administration.

## Architecture

- `frontend/` — React, TypeScript, Vite, and Supabase browser authentication.
- `backend/` — FastAPI API, Alembic migrations, PostgreSQL, and Appwrite-backed
  private attachment storage.
- `ai_review_service/` — optional human-in-the-loop expense review service.
- `receipt_intelligence_service/` — receipt OCR and metadata analysis service.
- `policy_assistant_service/` — policy-grounded retrieval assistant.
- `deployment/terraform-azure/` — Azure Container Apps and related production
  infrastructure.
- `.github/workflows/` — CI, security scanning, and deployment automation.

## Requirements

- Python 3.14 and [uv](https://docs.astral.sh/uv/) for the core API.
- Python 3.11 or later for the advisory services.
- Node.js 22 and npm for the frontend.
- PostgreSQL 16 or later. Docker is optional for local infrastructure.

## Quick start

### 1. Configure the API

Create `backend/.env` with development values. At minimum:

```dotenv
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/reimbursement
JWT_SECRET=replace-with-a-local-secret
AUTH_PROVIDER=local
CORS_ORIGINS=http://localhost:5173
```

For Supabase browser authentication, set `AUTH_PROVIDER=supabase` and configure
`SUPABASE_URL` plus either `SUPABASE_JWKS` or `SUPABASE_JWT_SECRET`. Keep
service-role credentials out of the frontend.

Start PostgreSQL, install dependencies, apply migrations, and run the API:

```bash
cd backend
docker compose up -d
uv sync
uv run alembic upgrade head
uv run python -m uvicorn app.main:app --reload
```

The API health endpoints are available at `http://localhost:8000/api/health`
and `http://localhost:8000/api/ready`.

### 2. Configure and run the frontend

Create `frontend/.env.local`:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

Then start Vite:

```bash
cd frontend
npm ci
npm run dev
```

### 3. Run optional advisory services

Run each service in its own terminal when the corresponding integration is
enabled:

```bash
cd ai_review_service && uv sync && uv run python -m uvicorn ai_review_service.api:create_app --factory --port 8011
cd receipt_intelligence_service && uv sync && uv run python -m uvicorn receipt_intelligence_service.api:create_app --factory --port 8012
cd policy_assistant_service && uv sync && uv run python -m uvicorn policy_assistant_service.api:create_app --factory --port 8013
```

## Validation

Run the same primary checks used by CI:

```bash
cd backend && uv run pytest tests -q
cd frontend && npm run lint && npm run test && npm run build
cd ai_review_service && uv run pytest -q
cd receipt_intelligence_service && uv run pytest -q
cd policy_assistant_service && uv run pytest -q
```

## Deployment

Merges to `main` run the GitHub Actions deployment workflow. It applies
migrations, builds the service images, deploys Azure Container Apps and the
frontend, then verifies API health, readiness, and route registration.

Production configuration is injected through GitHub/Azure secrets. Required
values include the production database URL, JWT/Supabase configuration,
frontend Supabase values, and storage/service credentials. Never commit those
values to this repository.

## Security notes

- The API enforces organization scope and permission checks on protected routes.
- Browser clients use the Supabase anonymous key only; service-role keys remain
  server-side.
- Attachments are accessed through authenticated API routes rather than public
  object URLs.
- CI runs tests, Terraform validation, CodeQL, and secret scanning.
