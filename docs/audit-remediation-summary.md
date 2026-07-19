# Audit remediation summary

This document records the source-controlled remediation of the 33 findings in
`REPOSITORY_AUDIT_REPORT.md`.  It is intentionally not a production release
attestation: the evidence that requires an Azure, Supabase, GitHub, email, or
edge-security environment is listed as an external gate below.

## Verification performed locally

- `uv run --directory backend pytest tests -q` — 105 passed.
- `uv run --directory ai_review_service pytest -q`, `receipt_intelligence_service`,
  and `policy_assistant_service` — 21, 11, and 8 passed.
- Fresh SQLite and PostgreSQL 16 `alembic upgrade head` plus `alembic check` passed.
- `cd frontend && npm run lint && npm run test && npm run build && npm run test:e2e`
  passed; the production-target rejection test passed separately.
- Terraform formatting, offline validation, deployment-contract validation,
  Docker Compose validation, and four service image builds passed.
- Runtime dependency lock checks and `npm audit --omit=dev --audit-level=high`
  passed.  CI workflow linting was also run with Actionlint.

## Finding ledger

| Finding | Source-controlled result and evidence | Remaining external release evidence |
| --- | --- | --- |
| AUD-001 | Fixed: authoritative Azure service contract, image digest deployment, and matching Terraform service definitions (`deployment/terraform-azure/service-contract.json`, `scripts/verify_deployment_contract.py`). | Staging revision health checks and all five service endpoints. |
| AUD-002 | Fixed: production configuration validation and durable PostgreSQL settings are declared in Terraform and service configuration. | Apply in staging; prove durable database connectivity and rollback. |
| AUD-003 | Fixed: remote `azurerm` backend and state protections are documented/configured; local state is ignored. | Bootstrap/migrate state, restrict state access, and retain migration evidence. |
| AUD-004 | Hardened: CI uses workload identity and no state/credential artifact is committed. | Rotate any previously exposed local/state credentials and remove accessible copies under the operator's retention process. |
| AUD-005 | Fixed: managed identity Blob backend is implemented and covered by backend tests. | Grant Blob data role, execute upload/retrieval/restart durability test. |
| AUD-006 | Fixed: scheduled Durable worker job and durable worker configuration are in Terraform. | Start job in staging and prove store-and-forward/retry execution. |
| AUD-007 | Fixed: tenant-scoped workflow/category/vendor models, policies, and cross-tenant authorization tests. | Run representative tenant-isolation smoke tests in staging. |
| AUD-008 | Fixed: transactional report submission, workflow resolution, and durable integration outbox. | Use the approved maintenance window for migration `009`, then prove retry/idempotency in staging. |
| AUD-009 | Fixed: durable AI-request and human-disposition outbox events with migration regression coverage. | Same maintenance-window deployment; verify consumers and replay behavior. |
| AUD-010 | Fixed: notification delivery lease/retry worker and tests. | Verify real delivery provider, retry timing, and dead-letter operations in staging. |
| AUD-011 | Mitigated: request-size, OCR/base64/pixel bounds, PII redaction, explicit provider config, and consent controls. | Confirm provider DPA/retention and organization consent before enabling external AI/OCR. |
| AUD-012 | Fixed: query cache is cleared on identity/tenant change and logout, with frontend tests. | Browser smoke test across two real tenant accounts. |
| AUD-013 | Fixed: env examples no longer carry unsafe credentials and local secret-file validation was added. | Rotate historical development credentials and verify secret-manager ownership. |
| AUD-014 | Fixed: Key Vault least privilege and purge protection are declared. | Verify actual role assignments, soft-delete/purge settings, and break-glass access. |
| AUD-015 | Fixed: worker receives required JWT, storage, and email/ACS configuration. | Configure sender identity and execute real notification job. |
| AUD-016 | Fixed: API route/database execution boundary is threadpool-safe; regression suite passes. | Load/stress test staging with production-shaped latency. |
| AUD-017 | Fixed in application: generic access-request acknowledgement, rate limits, and permission checks. | Enable edge WAF/CAPTCHA/abuse controls and test attack thresholds. |
| AUD-018 | Fixed: bounded, spooled uploads and defensive receipt/OCR processing. | Conduct staging load/large-file/zip-bomb security test. |
| AUD-019 | Fixed: organization/department fields and tenant catalog ownership are migrated and modeled. | Back up production and validate the legacy-data migration mapping in the maintenance window. |
| AUD-020 | Fixed: OAuth lifecycle reconciliation and explicit tenant identity handling. | Verify Supabase OAuth redirects, MFA/session settings, and account lifecycle against hosted configuration. |
| AUD-021 | Fixed: static web app deployment contract and documented host configuration. | Bind production hostname/origins and validate redirect/CORS behavior. |
| AUD-022 | Fixed: security headers and CSP are source-controlled. | Capture live headers and CSP violation telemetry after staging deployment. |
| AUD-023 | Fixed: payment dialog reset/error behavior has component tests. | Perform manual payment-flow acceptance test. |
| AUD-024 | Fixed: hermetic Playwright config rejects production-like E2E targets. | Wire staging-only CI target and retain CI run artifact. |
| AUD-025 | Fixed: contrast and Axe accessibility tests plus native form validation forwarding. | Complete keyboard/screen-reader acceptance pass on staging. |
| AUD-026 | Fixed: CI adds security checks, E2E, pinned actions/images, signing, SBOM, and provenance checks. | Enforce branch protection, required checks, environment reviewers, and OIDC/secrets in GitHub. |
| AUD-027 | Fixed: Supabase promotion configuration/runbook and safer auth storage behavior. | Apply hosted RLS/grants/backups/restore drill/JWT rotation and capture evidence. |
| AUD-028 | Fixed: deployment and operations guides cover Azure/Supabase setup and recovery. | Have the platform owner execute and sign off the runbooks. |
| AUD-029 | Fixed: logs, alerting/budget hooks, and operational runbook controls are declared. | Configure alert routes, budget thresholds, dashboards, and on-call response test. |
| AUD-030 | Fixed: Axios timeout, cancellation, bounded retry, and keep-alive overlap controls have tests. | Observe real client telemetry under staged network fault injection. |
| AUD-031 | Fixed: explicit session-storage auth persistence and associated tests. | Confirm browser policy and session behavior with hosted Supabase. |
| AUD-032 | Fixed: Radix Select forwards native validation through its hidden select; tests cover form behavior. | Complete browser/form acceptance testing. |
| AUD-033 | Fixed: floating receipt-service requirements file removed; lock-based dependency workflows and Docker builds validated. | Maintain dependency scanning and renovate/update policy in CI. |

## Required deployment order and rollback boundary

Migration `009_tenant_workflows_outbox` is a deliberate tenant-schema contract
change.  Take a verified backup, drain API writes and workers, run the migration,
deploy the matching backend and worker revision, smoke-test it, and only then
re-enable traffic.  The Azure workflow requires the maintenance approval gate
to match the deployed commit.  If validation fails before traffic resumes,
restore the backup and deploy the prior compatible revision; do not roll back a
partially applied schema by deleting state or data.

Consult [Azure production operations](azure-production-operations.md),
[Supabase production promotion](supabase-production-promotion.md), and
[backend security and operations](backend-security-operations.md) for the
operator checklists and evidence commands.
