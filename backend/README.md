# Core API

FastAPI owns reimbursement workflow, RBAC, audit records, policy validation, exports, and Neon persistence.

Deploy this container on AWS. Configure `DATABASE_URL` for Neon, Clerk verification settings, Appwrite storage/realtime settings, and private advisory-service URLs/tokens through AWS Secrets Manager. The API is the only service allowed to mutate reimbursement data.

```bash
uv sync
uv run alembic upgrade head
uv run pytest tests -q
uv run uvicorn app.main:app --reload
```
