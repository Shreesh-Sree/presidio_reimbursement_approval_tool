# Production readiness

## Required deployment controls

- Clerk: use production keys, enable Restricted sign-up mode, configure the production callback URL, and invite users only through administrators.
- Database: enforce daily encrypted backups, point-in-time recovery, and a quarterly restore drill into an isolated environment.
- Files: route uploads through malware scanning and quarantine before download or RAG indexing; enforce retention deletion for source files and derived OCR text.
- Observability: send errors to the approved error tracker, propagate `X-Request-ID`/trace IDs across services, and alert on API availability, queue backlog, failed OCR, email failure, and RAG-service failure.
- Security: keep the API behind TLS, restrict CORS to production origins, rotate service tokens/HMAC keys, run dependency scanning in CI, and review administrator audit logs.

## RAG assistant boundary

The Workspace Assistant is policy-only. Indexing is allowed only after a policy document has passed malware scanning and text extraction. Requests are tenant-scoped, use opaque references, require citations, and must not include employee, receipt, payment, or report content. The assistant is advisory and has no write/approval/payment capability.

## Release gate

1. Run backend, frontend, and microservice test suites.
2. Run Playwright against a dedicated Clerk test tenant and seeded data.
3. Apply migrations and run `alembic check`.
4. Verify health/ready endpoints, backup job, alert routing, and a restore drill.
5. Confirm Clerk restricted mode and production keys before traffic is enabled.
