# Policy assistant service

AWS-hosted, tenant/version-scoped policy RAG service. It indexes approved policy evidence and returns citations. It cannot access Neon, approve claims, or perform payments.

```bash
uv sync
uv run pytest -q
```
