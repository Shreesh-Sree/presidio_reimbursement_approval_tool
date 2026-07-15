# Presidio Policy Assistant

`policy_assistant_service` is an intentionally isolated, evidence-only RAG microservice. It explains the active policy text supplied to it; it **never** approves, rejects, routes, pays, or otherwise changes an expense report or workflow.

## Ownership and boundary

- It owns only `policy_assistant_service/` and its own SQLite file. It does not import the core backend, its ORM, the AI expense-review service, or their configuration.
- `POLICY_ASSISTANT_DATABASE_PATH` accepts only a local SQLite path. PostgreSQL and other network database URLs are rejected before the service opens a connection. Do not pass `DATABASE_URL` to this service.
- Every document and query is scoped by opaque `tenant_ref` and `policy_version_ref` values (for example `tenant-demo` and `policy-travel-v2`). Names, emails, URLs, and raw identifiers are rejected for scope references.
- Raw policy content stays local in the dedicated SQLite index. Questions are never persisted or logged. Structured logs contain only correlation IDs, endpoint metadata, opaque scope refs, and counts.
- `/v1/*` requires `Authorization: Bearer <POLICY_ASSISTANT_SERVICE_TOKEN>`. `/health` and `/ready` expose only liveness/readiness state and no policy content.

## RAG flow

1. An internal admin integration sends policy text to `POST /v1/policy-documents` with an opaque tenant, policy version, and document reference.
2. The service strips prompt-injection-like lines, redacts obvious email/phone contact data, normalizes text, and deterministically chunks the remaining policy evidence.
3. Each chunk gets a stable source ID and a local feature-hashed vector. Chunks and vectors are stored in the service's own SQLite tables.
4. `POST /v1/ask` rejects direct prompt injection, retrieves only the matching tenant + policy-version chunks, and returns excerpts with source chunk citations.
5. If retrieval has no evidence, the answer explicitly says that evidence is insufficient. The answer never invents a policy rule and always states its workflow-action boundary.

The document text is always untrusted **data**. Neither a document nor a question can provide instructions that alter this behavior. Suspicious document lines are removed and reported as non-sensitive flag names; suspicious questions are rejected with `422`.

## Retrieval trade-offs

The initial vector implementation uses deterministic token feature hashing and cosine similarity rather than a downloaded embedding model or hosted vector database. It is cheap, repeatable, works offline, and avoids sending policy content to a third party. Its trade-off is weaker semantic matching than a trained embedding model. A future upgrade may replace only the isolated `vector_store.py` adapter with a vetted embedding/vector provider after privacy, retention, cost, and retrieval-quality evaluation.

`POLICY_ASSISTANT_PROVIDER_MODE` recognizes `deterministic`, `openrouter`, and `huggingface`, but the default is `deterministic` and `POLICY_ASSISTANT_ENABLE_EXTERNAL_PROVIDER=false`. This version makes **no external model calls**, even if a provider name is configured. That explicit disabled-by-default gate prevents accidental data egress during local development.

## Local run

```bash
cd policy_assistant_service
cp .env.example .env
# Replace the example token in .env with a long random local secret.
uv sync --group dev
uv run uvicorn policy_assistant_service.api:create_app --factory --host 127.0.0.1 --port 8013
```

Index a policy document:

```bash
curl -X POST http://127.0.0.1:8013/v1/policy-documents \
  -H 'Authorization: Bearer replace-with-your-local-token' \
  -H 'Content-Type: application/json' \
  -d '{"tenant_ref":"tenant-demo","policy_version_ref":"policy-travel-v2","document_ref":"doc-travel-rules","content":"Airfare is reimbursable up to USD 500 per trip."}'
```

Ask a grounded question:

```bash
curl -X POST http://127.0.0.1:8013/v1/ask \
  -H 'Authorization: Bearer replace-with-your-local-token' \
  -H 'Content-Type: application/json' \
  -d '{"tenant_ref":"tenant-demo","policy_version_ref":"policy-travel-v2","question":"What is the airfare cap?"}'
```

## Testing

```bash
cd policy_assistant_service
uv run pytest -q
```

The focused test suite verifies bearer authentication, PII-safe scope contracts, exact tenant isolation, source-grounded citations, and direct/indirect prompt-injection defenses.
