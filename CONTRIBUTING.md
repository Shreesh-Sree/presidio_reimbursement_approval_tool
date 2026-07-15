# Contributing

Thank you for improving the reimbursement approval tool.  This repository
contains a React client, a FastAPI core service, three isolated advisory/data
services, and AWS Terraform.  Changes should keep those boundaries clear.

## Working agreement

1. Start from an up-to-date `main` branch and use a short-lived branch or
   worktree for one logical change.
2. Use names such as `feat/report-status`, `fix/receipt-validation`,
   `docs/learning-matrix`, or `chore/ci-cache`.
3. Prefer test-first work for behavior changes: add or update the failing test,
   implement the smallest correct change, then run the focused suite.
4. Open a pull request rather than pushing directly to `main`.
5. Keep commits conventional and focused, for example:

   ```text
   feat(fe): add approval status timeline
   fix(api): prevent submitting a report with policy violations
   test(ai): cover duplicate receipt digest finding
   docs: describe AI data-retention boundary
   ```

## Local checks

Run only the checks relevant to your change while iterating, then run the
complete affected suite before requesting review.

```bash
# Backend
cd backend
uv sync
uv run pytest tests -q
uv run alembic check

# Frontend
cd ..
cd frontend
npm ci
npm run lint
npm run test
npm run build

# Advisory AI service
cd ..
cd ai_review_service
uv sync
uv run pytest -q

# Receipt intelligence service (digest metadata only; separate SQLite store)
cd ..
cd receipt_intelligence_service
uv sync
uv run pytest -q

# Policy assistant service (tenant/version-scoped RAG; separate SQLite store)
cd ..
cd policy_assistant_service
uv sync
uv run pytest -q

# Terraform validation only: never apply from an unreviewed branch.
cd ..
terraform fmt -check -recursive deployment/terraform
terraform -chdir=deployment/terraform init -backend=false
terraform -chdir=deployment/terraform validate
terraform -chdir=deployment/terraform/bootstrap init -backend=false
terraform -chdir=deployment/terraform/bootstrap validate
```

The CI workflow runs equivalent checks with an ephemeral PostgreSQL service
for Alembic.  It never deploys, uploads artifacts, pushes container images, or
changes cloud resources.

## Review standards

- Describe the user-facing behavior and link the issue or requirement.
- Include tests for success, validation/error, and permission paths where they
  apply.
- Keep API routes thin; put business rules in services and preserve audit
  logging/state-transition invariants.
- Include a migration when a persistent model changes.  Test upgrade and
  metadata consistency with Alembic.
- Use responsive, keyboard-accessible UI.  Preserve loading, empty, and error
  states when changing a frontend query or mutation.
- Keep all isolated services within their boundaries.  AI review may not
  mutate reimbursement workflow data; receipt intelligence may not receive raw
  receipt files or URLs; and the policy assistant may not share the core
  database, persist questions, or return uncited policy claims.
- Preserve finance state-machine/audit invariants and delegation/SLA provenance
  when changing payment or approval workflow code.
- Update [`docs/LEARNING_MATRIX.md`](docs/LEARNING_MATRIX.md) or an ADR when a
  change introduces a material architecture, privacy, cost, or reliability
  decision.

## Security and secrets

- Never commit `.env` files, database URLs, JWT/service-provider keys, AWS
  credentials, Terraform state, generated secret values, or uploaded files.
- Use `.env.example` files for variable names and safe placeholders only.
- Do not put secrets in test fixtures, screenshots, logs, prompts, issues, or
  pull-request descriptions.
- Do not put raw policy documents, receipt text, receipts, employee identities,
  or report descriptions into an external model/provider without an explicit
  privacy, retention, and vendor review.
- Report a suspected secret exposure privately to a repository administrator;
  rotate the credential before removing it from history.
- Do not bypass the secret scan or required status checks without an incident
  record and follow-up remediation.

## Database and infrastructure changes

- Migrations must be forward-only, reversible where practical, and compatible
  with the existing production data model.
- Treat the configured development database as shared data: tests should use
  their isolated fixtures rather than destructive commands against it.
- Terraform plans/applies require explicit authorization and a reviewed
  environment configuration.  Do not run `terraform apply` as part of a PR or
  routine local validation.
- Do not add fixed-cost cloud services merely to demonstrate a technology.
  Record the scaling trigger and budget effect first.

## Pull requests and branch protection

Use the checklist in [`.github/pull_request_template.md`](.github/pull_request_template.md).
Repository administrators should configure the protections in
[`.github/BRANCH_PROTECTION.md`](.github/BRANCH_PROTECTION.md) before relying
on `main` for releases.  A starter ownership file lives at
[`.github/CODEOWNERS.example`](.github/CODEOWNERS.example); replace the example
owners with real GitHub users or teams before enabling required code-owner
reviews.
