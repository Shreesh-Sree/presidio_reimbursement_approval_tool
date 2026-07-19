# Azure production deployment and operations runbook

This is the authoritative production runbook for the Azure path. It replaces
the retired imperative setup scripts. It describes source-controlled changes
and the operator actions that cannot be performed from this repository.

## Release boundary

- Terraform owns Azure Container Apps, Key Vault, ACR, Blob storage, logging,
  runtime identities, alert routing, and their configuration.
- GitHub Actions builds one image for each entry in
  `deployment/terraform-azure/service-contract.json`, attaches SBOM and
  provenance attestations, signs its immutable digest, and passes only those
  digests to Terraform.
- No operator should run `az containerapp update` for a release. Re-run the
  workflow from the intended commit instead, so Terraform remains authoritative.
- Azure Static Web Apps is deployed by its separate pinned action; its API and
  redirect origins must still be changed through the protected environment.

## One-time external bootstrap

These steps require an Azure/GitHub administrator and are deliberately not run
by repository automation.

1. Create a dedicated state resource group, storage account, and private
   container. Require HTTPS, disable public Blob access and shared-key access,
   use Azure AD/OIDC authentication, and retain/delete-protect state according
   to the organisation's incident policy.
2. Provision a VNet-connected self-hosted GitHub Actions runner before enabling
   Private Link. It needs private DNS resolution for ACR, Key Vault, Blob, and
   the remote state endpoint. GitHub-hosted `ubuntu-latest` runners cannot be
   assumed to reach those private endpoints.
3. Give the GitHub production OIDC principal only the scopes it needs:
   resource-group Contributor (not subscription Contributor), ACR Push on the
   project registry, Key Vault Secrets Officer on the project vault for the
   deployment phase, and Storage Blob Data Contributor on the *state* container.
   Grant User Access Administrator only through a separately controlled
   bootstrap identity if role assignment creation is required.
4. Create the GitHub `azure-production` environment with required reviewers,
   deployment branches limited to `main`, and environment-scoped secrets. Verify
   branch protection requires CI, CodeQL, and the supply-chain job.
5. Bootstrap the ACR from the protected Terraform environment before the first
   image build. A targeted, reviewed `module.registry` apply is permitted only
   for this chicken-and-egg step; immediately follow it with a normal workflow
   release. Do not create placeholder Container Apps by CLI.
6. Before the first apply, grant the deployment identity Key Vault Secrets
   Officer at the vault. The Terraform module intentionally does not grant its
   own deployment identity data-plane privilege.

Set these protected GitHub environment values (not repository files):

| Category | Required names |
| --- | --- |
| Azure/OIDC secrets | `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `ACR_LOGIN_SERVER` |
| Terraform state variables | `TF_BACKEND_RESOURCE_GROUP`, `TF_BACKEND_STORAGE_ACCOUNT`, `TF_BACKEND_CONTAINER`, `TF_BACKEND_KEY` |
| Terraform environment variables | `AZURE_RESOURCE_GROUP`, `AZURE_LOCATION`, `AZURE_PROJECT_NAME`, `CORS_ORIGINS`, `OPERATIONS_OWNER`, `COST_CENTER`, `ALERT_EMAIL`, `AZURE_COMMUNICATION_SENDER`, `KEY_VAULT_SECRET_EXPIRATION_DATE`, `STORAGE_CMK_KEY_EXPIRATION_DATE` |
| Release-only protected variable | `BREAKING_MIGRATION_MAINTENANCE_APPROVED` — exact target commit SHA, set only after the write drain and clear after the release |
| Private-network protected variables | `AZURE_PRIVATE_RUNNER_LABEL` — VNet-connected runner label; `PRIVATE_NETWORK_DEPLOYMENT_READY=true` only after the documented cutover has completed |
| Core runtime secrets | `DATABASE_URL`, `JWT_SECRET`, `SUPABASE_JWT_SECRET`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPER_ADMIN_EMAIL` |
| Email-delivery secret | `AZURE_COMMUNICATION_CONNECTION_STRING` — non-empty only when `EMAIL_DELIVERY_ENABLED=true`; the sender must be a verified ACS sender |
| Advisory runtime secrets | `AI_REVIEW_SERVICE_TOKEN`, `AI_REVIEW_DATABASE_URL`, `AI_REVIEW_REFERENCE_HMAC_KEY`, `RECEIPT_INTELLIGENCE_SERVICE_TOKEN`, `RECEIPT_INTELLIGENCE_DATABASE_URL`, `POLICY_ASSISTANT_SERVICE_TOKEN`, `POLICY_ASSISTANT_DATABASE_URL`, `POLICY_ASSISTANT_REFERENCE_HMAC_KEY` |
| Frontend secrets/variables | `AZURE_STATIC_WEB_APPS_API_TOKEN`, `VITE_SUPABASE_ANON_KEY`, `VITE_SUPABASE_URL`, `VITE_API_BASE_URL`, `API_BASE_URL` |

`CORS_ORIGINS` is a comma-separated list of exact HTTPS origins. Wildcards are
rejected by Terraform and the backend outside explicit local/test modes.
`VITE_API_BASE_URL` is the browser-facing API base including the `/api` path
(for example, `https://api.example.com/api`, with no trailing slash).
`API_BASE_URL` is the matching API origin without `/api` (for example,
`https://api.example.com`), because the release verification appends
`/api/health` and `/api/ready`. Set both to the same production route; neither
value is a secret.

When `EMAIL_DELIVERY_ENABLED=true`, Terraform and the backend reject a blank
ACS connection string or sender rather than falling back to localhost SMTP.
Confirm the sender is verified in Azure Communication Services and send a
staging test message before enabling production delivery.

`KEY_VAULT_SECRET_EXPIRATION_DATE` and `STORAGE_CMK_KEY_EXPIRATION_DATE` must
be deliberate RFC 3339 UTC rotation deadlines (for example,
`2027-01-31T00:00:00Z`). Updating only an expiry date is not rotation: rotate
the underlying secret/key through the approved ownership process before its
deadline.

## Private Link and Checkov rollout

The Terraform configuration disables public access to ACR, Key Vault, and Blob
storage; creates private endpoints and DNS zones; enables Storage CMK; and
attaches Container Apps to a dedicated private subnet. This is a **blue/green
network migration**, not an in-place production change:

1. Reserve non-overlapping CIDRs. The current Consumption Container Apps
   environment needs a dedicated, undelegated `/23`-or-larger infrastructure
   subnet; private endpoints use a different subnet.
2. Build the VNet, private DNS links, and VNet-connected runner using a reviewed
   bootstrap path. Verify that the runner resolves ACR, Key Vault, Blob, and
   Terraform state endpoints to private addresses.
3. Create a new Container Apps environment and registry path where required;
   `infrastructure_subnet_id` and legacy ACR zone configuration can force
   replacement. Copy/import signed images, assign the existing managed roles,
   and smoke-test image pulls, Key Vault references, Blob access, and public API
   ingress before switching DNS/traffic.
4. Set `AZURE_PRIVATE_RUNNER_LABEL` and only then set
   `PRIVATE_NETWORK_DEPLOYMENT_READY=true` in the protected environment. The
   deploy workflow intentionally fails before any private data-plane operation
   when either guard is absent.

Five Checkov controls are intentionally skipped inline, not globally: ACR
Docker Content Trust is retired for new registries (Cosign/digest/provenance
are enforced instead); image quarantine requires a future approve/unquarantine
workflow; geo-replication requires an approved DR region; legacy zone settings
can replace ACR; and legacy Storage Insights conflicts with keyless storage.
Azure Monitor Blob diagnostics are configured as the compensating logging
control. Reassess each exception at least annually and before changing the
release architecture.

## State and credential incident response

Treat a local Terraform state file or backup that contains Key Vault secret
values as exposed. Do not print it, attach it to tickets, or delete it without
the retention/forensics owner's approval.

1. Open an incident with the security owner and identify the state file's
   access period and every secret category it held.
2. Rotate the affected database, Supabase, JWT, provider, inter-service, SMTP,
   and deployment credentials at their owning systems. Revoke old values.
3. Update only the protected GitHub/Key Vault inputs, then deploy a reviewed
   release and validate that old credentials fail.
4. Move state to the remote Azure AD/OIDC backend, verify state access logs and
   container RBAC, then use the approved secure-removal procedure for local
   copies/backups.
5. Record the rotation, affected revisions, and validation evidence in the
   incident record. Never put values in this repository.

## Normal release and rollback

1. Confirm CI is green, the production environment has approved the run, and
   the intended database migration is backward compatible. Migration 009 is
   deliberately **not** backward compatible; use the controlled procedure
   below instead.
2. The workflow builds digest-addressed images, emits SBOM/provenance, signs
   them, runs migrations, plans Terraform with a remote state lock, applies
   only plan exit code `2`, and verifies each running revision's digest.
3. Validate `/api/health`, `/api/ready`, intended CORS preflight, advisory
   health/readiness, and a staging attachment restart test.

To roll back application code, select a previously verified commit in the
deployment workflow (or revert the release commit) and let Terraform apply the
prior immutable digests. Do not use a mutable tag or imperative image update.
Database migrations are not automatically reversible: restore from a tested
backup or run a separately reviewed forward-fix migration. Capture the prior
revision/digests before every release.

## Controlled release for migration 009 (tenant ownership)

`009_tenant_workflows_catalogs_and_outbox` makes tenant ownership mandatory
for workflow rules, categories, vendors, and durable work. An old backend or
worker can write rows that violate that new contract. It is therefore blocked
in CI until the protected `azure-production` environment variable
`BREAKING_MIGRATION_MAINTENANCE_APPROVED` equals the exact commit SHA being
deployed. A value such as `true` is intentionally rejected. Set it only for
the planned commit and clear it immediately after the release.

Perform every step in one approved maintenance window; do not run old and new
backend/worker binaries concurrently.

1. Record the target commit SHA, current Container App revisions/digests, and
   `alembic current`. Take and verify a restorable production PostgreSQL
   backup before changing traffic.
2. Put the approved edge/gateway/frontend maintenance control in front of the
   API and prove that every external write method (`POST`, `PUT`, `PATCH`, and
   `DELETE`) is rejected. Drain in-flight writes using the API timeout, then
   suspend the scheduled worker through the approved Azure operations control
   and wait for any active execution to finish. Keep evidence in the change
   record.
3. In the protected GitHub environment, set
   `BREAKING_MIGRATION_MAINTENANCE_APPROVED` to that exact target SHA. Re-run
   the deployment workflow for that SHA. Its migration job now performs
   `alembic upgrade head`; it otherwise fails before any schema change.
4. Let Terraform deploy the matching immutable backend and worker digest while
   the write maintenance control remains active. Verify `/api/health`,
   `/api/ready`, the deployed digest, `alembic current`, and `alembic check`.
   Smoke-test a report submission, workflow lookup, category/vendor
   administration, policy document access, and a cross-tenant attachment
   denial using the new revision.
5. Re-enable the scheduled worker, remove the maintenance response, and prove
   a write succeeds. Clear `BREAKING_MIGRATION_MAINTENANCE_APPROVED` from the
   protected environment so a later commit requires a new approval.

Do not use an Alembic downgrade as routine recovery after new writes. Restore
the verified pre-migration backup or use a separately reviewed, data-preserving
forward fix. The backend-specific procedure is also recorded in
[`backend-security-operations.md`](backend-security-operations.md).

## Blob storage and durable advisory state

Terraform gives only the backend identity `Storage Blob Data Contributor` on
the uploads container. Production sets `STORAGE_BACKEND=azure`,
`AZURE_STORAGE_ACCOUNT_URL`, and `AZURE_STORAGE_CONTAINER`; it does not inject
a storage account connection string. Confirm externally that the role is
effective, public access and shared keys are disabled, and network controls
meet the chosen architecture.

Each advisory service receives a distinct PostgreSQL URL and must run with
`*_ENVIRONMENT=production` and `*_PERSISTENCE_BACKEND=postgresql`. SQLite is
allowed only in explicit local/test configurations. After each staging release:

1. Upload a synthetic receipt and a synthetic policy document.
2. Record an advisory job/index result.
3. Restart/revise each Container App without changing its digest.
4. Confirm authorised download, duplicate observation, and policy/review state
   remain available; confirm a different tenant cannot read the attachment.

Terraform also deploys a single-replica Container Apps Job every five minutes
from the same immutable backend digest. It runs `python -m app.worker --once`
to claim durable email/outbox/SLA work. Verify the job's execution history,
lease recovery, and dead/retry rows in staging after any worker or schema
change; do not rely on API background tasks as the scheduler.

## Operational readiness

The Terraform module creates a Log Analytics workspace, a production action
group, and a Container App failure query alert. Before release, an operator
must fire and acknowledge a staging test alert, confirm the KQL table/schema,
and configure an on-call escalation path beyond email if required.

| Signal / objective | Initial target | Alert / review |
| --- | --- | --- |
| Core API availability | 99.9% monthly successful `/api/health` and `/api/ready` checks | Page after 10 minutes of failed external synthetic checks |
| API latency | p95 under 750 ms excluding uploads | Investigate sustained 15-minute breach |
| Attachment durability | zero lost synthetic objects after revision restart | Page on Blob auth/5xx errors and run restart test per release |
| Advisory processing | no stuck/repeated jobs; readiness 99.5% | Page on Container App failure/restarts; daily queue review |
| Recovery | RPO 24 hours, RTO 4 hours until a stricter approved target exists | Quarterly restore exercise with evidence |

Run a quarterly restore drill for Supabase data, a Blob version/recovery drill,
and a revision rollback drill. Validate database backups, Blob versioning and
30-day soft delete, Key Vault recovery settings, logs retention, alert routing,
and documented owner contacts. These are external runtime verifications.

All Terraform resources receive `project`, `environment`, `owner`,
`cost_center`, `data_classification`, and `managed_by` tags. The cloud finance
owner must create a subscription/resource-group budget, anomaly alert, ACR
retention policy, and log/storage retention review in Azure; record the budget
threshold and owner in the operational ticket. Do not claim those hosted
controls are active until verified.
