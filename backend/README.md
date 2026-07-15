# Reimbursement API

The FastAPI application lives in `app.main` and uses Alembic migrations plus
the models registered by `app.models`.

```bash
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Run `uv run pytest tests -q` for backend tests and `uv run alembic check` to
confirm migrations match metadata. `main:app` remains a compatibility alias
for existing local commands.

File bytes are stored through `app.services.storage_service` (`local` by
default; S3 when `STORAGE_BACKEND=s3`). AI review is intentionally not an API
module: configure `AI_REVIEW_SERVICE_URL` to connect to the separately deployed
`../ai_review_service`.
