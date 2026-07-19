# Production deployment setup

This repository has one supported Azure release path: the pinned GitHub Actions
workflow plus `deployment/terraform-azure`. Terraform is the source of truth
for Container Apps and their digest-addressed images. Do not create or update
Container Apps manually with `az containerapp` commands.

Start with the [Azure production operations runbook](docs/azure-production-operations.md).
It contains the required remote-state, identity, Key Vault, Blob, alerting,
backup, cost, release, rollback, and credential-rotation steps. Those steps
need privileged external approval and are intentionally not automated here.

## Authoritative runtime contract

| Workload | ACR repository | Container port | Ingress |
| --- | --- | ---: | --- |
| Core API | `backend` | 8000 | External |
| AI Review | `ai-review-service` | 8011 | Internal |
| Receipt Intelligence | `receipt-intelligence-service` | 8012 | Internal |
| Policy Assistant | `policy-assistant-service` | 8013 | Internal |

The executable source for this table is
[`service-contract.json`](deployment/terraform-azure/service-contract.json).
CI validates it against Dockerfiles and Terraform before deployment.

## Required configuration

Configure the `azure-production` GitHub environment with the names listed in
the Azure runbook. Important conventions:

- `CORS_ORIGINS` contains explicit comma-separated origins only; `*` is
  rejected.
- `TF_BACKEND_*` identifies an Azure AD/OIDC remote state backend. No local
  state, state key, or `terraform.tfvars` belongs in Git.
- Every service image is supplied as a `sha256:` digest from the build job;
  `latest` is never deployed.
- The core API uses managed identity to access Azure Blob (`STORAGE_BACKEND=azure`),
  never a production storage connection string.
- Advisory services require their own PostgreSQL URL, service token, and
  production persistence configuration. SQLite is local/test only.

## Deployment sequence

1. CI runs tests, hermetic browser tests, Terraform/configuration contract
   checks, secret scanning, CodeQL, IaC/container scanning, and an SBOM job.
2. The protected deployment builds, signs, attests, and pushes immutable ACR
   images.
3. Alembic applies only after the protected maintenance gate. Compatible
   migrations may proceed normally; migration 009 is a breaking tenant
   contract migration and follows the drain/backup/migrate/deploy/re-enable
   procedure in the Azure operations runbook.
4. Terraform plans against locked remote state and applies only a successful
   changed plan.
5. The workflow verifies the digest on every Container App revision, then API
   health/readiness. Operators complete the deeper staging smoke checks in the
   runbook.

## Unsupported paths

- `scripts/azure-setup.sh` and `scripts/setup-github-secrets.sh` are retired;
  they must not be used to create infrastructure or write GitHub secrets.
- Floating `receipt_intelligence_service/requirements.txt` is removed. Use
  `uv sync --frozen` with the committed `uv.lock` files.
- Seed/reset SQL scripts are not production deployment tools. Review them only
  in isolated non-production databases.

## Supabase/Auth

Follow [Supabase/Auth production promotion](docs/supabase-production-promotion.md)
for hosted-console checks, exact redirect URLs, signup policy, MFA, RLS,
backups, and OAuth provider configuration. The source baseline is not proof of
the hosted project's effective settings.
