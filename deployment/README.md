# AWS deployment

This folder deploys the complete reimbursement application as a deliberately
small AWS production/pilot footprint. It preserves the application's important
boundary: the FastAPI reimbursement service and each advisory AI service run as
separate private containers with their own local SQLite datastore. The AI
services have no database credentials for the reimbursement system, cannot
reach the EC2 metadata role endpoint, and are never exposed to the public
internet.

The target is **under USD 75/month in `us-east-1` for a small team and modest
traffic**. It is a single-host, Single-AZ cost profile, not an HA/SLA profile.
AWS Budgets alerts are included, but they are delayed notifications—not a hard
spending cutoff.

## Architecture

```text
Browser
  │
  ├─ OAuth ──> Clerk (hosted sign-in and social identity providers)
  │
  ├─ HTTPS ──> CloudFront + ACM ──> private S3 bucket (React/Vite SPA)
  │                  │
  │                  └─ Route 53: app.<domain>
  │
  └─ HTTPS ──> Route 53: api.<domain> ──> Elastic IP ──> EC2 + Caddy
                                                              │ segmented Docker networks
                                                              ├─ FastAPI API ──> RDS PostgreSQL
                                                              │       │              (private subnets)
                                                              │       ├─> private S3 uploads bucket
                                                              │       ├─> AI-review (internal network + SQLite)
                                                              │       ├─> Receipt intelligence (internal network + SQLite)
                                                              │       └─> Policy assistant (internal network + SQLite)
                                                              └─ Caddy reaches FastAPI only

EC2 instance profile ──> ECR, Secrets Manager, S3, CloudWatch Logs, SSM
SES + Route 53 ──> verified sender / optional SMTP delivery
CloudWatch + SNS ──> operational alarms
AWS Budgets ──> $60 / $70 / $75 forecast and actual-spend alerts
```

## Services and why each is here

| AWS service | Purpose | Cost-conscious choice |
| --- | --- | --- |
| Amazon EC2 | Runs Caddy, FastAPI, and three separately isolated advisory AI containers. | One `t3a.small` host rather than separate always-on container platforms. |
| Amazon RDS for PostgreSQL | Durable transactional reimbursement database. | `db.t4g.micro`, encrypted gp3, private, Single-AZ. |
| Amazon S3 | Private receipts/policy documents, private SPA assets, and Terraform state. | Lifecycle cleanup and no direct public access. |
| Amazon CloudFront + ACM | HTTPS SPA delivery and TLS certificate. | `PriceClass_100`, no paid WAF tier. |
| Amazon ECR | Versioned API and isolated AI container images. | Four repositories, scan on push; lifecycle keeps five images each. |
| Amazon Route 53 | DNS for `app` and `api`, ACM DNS validation, SES records. | Uses an existing hosted zone. |
| AWS Secrets Manager | Separate core-runtime and advisory-service runtime secrets fetched by the EC2 role. | Every advisory secret contains only its own token/local SQLite settings—never database, JWT, SMTP, or S3 credentials. |
| Amazon SES | Optional status-change email delivery. | Domain/DKIM setup only; SMTP delivery remains disabled by default. |
| Amazon CloudWatch + SNS | 14-day container logs and four capacity/storage alarms. | Five bounded container log groups; no high-resolution metrics, dashboards, or log archive. |
| AWS Systems Manager | Shell-free, keyless image rollout and break-glass administration. | No SSH port or EC2 key pair. |
| AWS Budgets | Forecast notifications before the monthly cap. | Monitoring alerts have no action automation cost. |
| Amazon VPC + S3 Gateway Endpoint | Isolated database and private S3 path. | No NAT Gateway or paid interface endpoint. |

## Budget guardrails

The concrete configuration excludes the common fixed-cost traps: **no NAT
Gateway, ALB/NLB, EKS, Multi-AZ RDS, dedicated SES IP, paid WAF rules, VPC
interface endpoint, or duplicate always-on compute**.

| Expected monthly driver in `us-east-1` | Planning range (USD) |
| --- | ---: |
| `t3a.small`, 20 GiB gp3, one public IPv4 | 18–20 |
| `db.t4g.micro`, 20 GiB RDS gp3, backups | 14–18 |
| Route 53 + four Secrets Manager values + four basic alarms | 3–4 |
| ECR, S3, CloudFront, CloudWatch logs, and SES at modest traffic | 3–15 |
| **Expected total** | **38–57** |

That leaves roughly $18 of headroom for normal variation. Traffic, unusually
large uploads, CloudFront egress, a resize, or optional Groq/provider usage
can still exceed the cap. The root module creates forecast **and actual-spend**
alerts at 80%, about 93%, and 100% of the configured limit (USD 60/70/75 at
the default). Confirm
both the AWS Budgets and SNS subscription emails after the first apply.

Pricing references: [RDS for PostgreSQL](https://aws.amazon.com/rds/postgresql/pricing/),
[public IPv4](https://aws.amazon.com/vpc/pricing/),
[AWS Budgets](https://aws.amazon.com/aws-cost-management/aws-budgets/pricing/),
[Secrets Manager](https://aws.amazon.com/secrets-manager/pricing/),
[ECR](https://aws.amazon.com/ecr/pricing/), and
[SES](https://aws.amazon.com/ses/pricing/). Recheck the AWS Pricing Calculator
for your chosen region before applying.

## Prerequisites

- Terraform >= 1.7, AWS CLI v2, Docker Buildx, Node/npm, and credentials that
  can provision the services above.
- A registered domain with an existing Route 53 public hosted zone.
- A least-privilege local deploy identity. Runtime AWS permissions are created
  separately as the EC2 instance profile.
- An AWS account where the selected `t3a.small` and `db.t4g.micro` are
  available. Change the variables only after reviewing the budget impact.
- A Clerk application with the intended OAuth providers enabled. This deployment
  verifies Clerk JWTs with the JWKS endpoint, so it does **not** use or need a
  Clerk secret key on the runtime host.

## Clerk OAuth and access gate

The SPA uses Clerk for sign-in only; the API remains the authorization source.
It accepts only Clerk JWTs that match the configured issuer, audience, and
authorized browser origins. On the first successful OAuth sign-in,
`super_admin_email` is provisioned as Super Admin using the configured default
organization and department. After that, administrators create the email
allowlist through the application. A signed-in identity not on that allowlist
is deliberately sent to the explicit no-access page.

Before applying, create a Clerk JWT template (the default name is
`presidio-api`) for API tokens. Copy its issuer, audience, and JWKS URL into
the Terraform values, and include `https://app.<your-domain>` in
`clerk_authorized_parties`. The signed custom token must use RS256 and include
the verified sign-in email claims expected by the API, for example:

```json
{
  "email": "{{user.primary_email_address}}",
  "email_verified": "{{user.email_verified}}",
  "aud": "presidio-api"
}
```

Set `clerk_audience` to the exact static `aud` value above (or the value chosen
in your template). Clerk supplies standard `iss`, `sub`, and `azp` claims; the
API checks all of them. Configure the same `clerk_jwt_template` in the frontend
build values.

`clerk_publishable_key` and `clerk_jwt_template` are public browser build
configuration. The deployment script reads them from Terraform outputs and
passes them as `VITE_CLERK_PUBLISHABLE_KEY` and `VITE_CLERK_JWT_TEMPLATE` at
build time. Do not treat the publishable key as a secret; it will be visible in
the compiled SPA. Do not add a Clerk secret key to this stack.

The API receives `AUTH_PROVIDER=clerk`, Clerk verifier metadata, the Super
Admin email, and organization defaults only from its `0600` Secrets Manager
runtime env file. Keep the real Super Admin email and all provider keys out of
version control. `terraform.tfvars` is ignored; prefer `TF_VAR_super_admin_email`
and a protected CI secret for production.

In the Clerk Dashboard, enable only the required OAuth/social connections and
disable email/password, email-code, email-link, and self-service credential
sign-up methods. The application has no manual credential UI, but Clerk’s
hosted component follows the sign-in methods enabled in that dashboard.

## First deployment

Terraform state contains generated database, JWT, service-to-service, and
sensitive provider values. **Create encrypted remote state before applying the
main stack.**

1. Bootstrap the state bucket once. Do not point this bootstrap configuration
   at the bucket it is creating.

   ```bash
   cd deployment/terraform/bootstrap
   cp terraform.tfvars.example terraform.tfvars
   # Edit state_bucket_name to a globally unique value.
   terraform init
   terraform apply
   ```

2. Configure the main stack.

   ```bash
   cd ..
   cp terraform.tfvars.example terraform.tfvars
   cp backend.hcl.example backend.hcl
   # Edit both files: use the state bucket output, domain/zone IDs, Clerk JWT
   # metadata, an allowlisted Super Admin email, ACME address, and budget-alert
   # email. Keep actual provider keys in protected environment/CI variables.
   terraform init -backend-config=backend.hcl
   terraform plan -out=tfplan
   terraform apply tfplan
   ```

   The EC2 runtime service retries image pulls every minute until the first
   images exist. CloudFront and ACM can take several minutes to finish.

3. Build and publish the four images, then start the private runtime with SSM.

   ```bash
   export AWS_REGION=us-east-1
   DEPLOY_RUNTIME=1 bash deployment/scripts/build-and-push.sh
   ```

4. Build the SPA with the Terraform-provided API URL and public Clerk values,
   upload it to its private bucket, and invalidate CloudFront.

   ```bash
   export AWS_REGION=us-east-1
   bash deployment/scripts/deploy-frontend.sh
   ```

5. Verify DNS/TLS, then sign in through Clerk as the configured Super Admin.
   There is no manual email/password bootstrap in the deployed application.

   ```bash
   curl "$(terraform -chdir=deployment/terraform output -raw api_health_url)"
   ```

For later backend/advisory-service releases, publish the deliberately mutable `stable` tag
and run the same `DEPLOY_RUNTIME=1` command. This small-host profile avoids a
replacement rollout so it preserves the AI service's advisory datastore;
immutable-tag releases need a future blue/green or separate-datastore design.

## Email and AI provider activation

The infrastructure creates SES domain, DKIM, MAIL FROM, SPF, and Route 53
records. SES is initially sandboxed in many accounts. Leave
`enable_email_delivery = false` until all of the following are complete:

1. SES reports the domain identity/DKIM as verified.
2. Production SES access has been approved if external recipients are needed.
3. You create dedicated SES SMTP credentials and set the two sensitive
   Terraform variables.
4. You apply the change and confirm an email status transition.

The AI reviewer, receipt intelligence service, and policy assistant are
deterministic and fully functional without a model key. To enable Groq for the
AI-review narrative, set `ai_review_provider = "groq"` and supply
`TF_VAR_groq_api_key` from a local secure shell or protected CI secret before
planning/applying. `groq_api_key` is sensitive and is written only to the
AI-review runtime secret; it is read only by that container. The optional
`groq_model` defaults to `openai/gpt-oss-20b`. Gemini remains available only
when selected explicitly and provided its own key. The policy assistant has
external provider use explicitly disabled in its own secret. Third-party model
costs are outside the AWS USD 75 budget: configure vendor-side usage limits and
rotate any key that has ever been pasted into a chat, terminal history, or
unprotected file.

## Advisory service isolation

The runtime uses one edge Docker network for Caddy and FastAPI plus a dedicated
private Docker network per advisory service. FastAPI is the only process
attached to all three advisory networks; Caddy is not attached to any of them
and the Caddyfile contains no advisory route. Receipt intelligence and policy
assistant networks are `internal: true`; AI review keeps private egress only
for its explicitly configured optional provider. Each service receives a
different `0600` env file generated from its own Secrets Manager secret and a
different host-backed directory:

| Service | Internal URL from FastAPI | Local datastore |
| --- | --- | --- |
| AI review | `http://ai-review:8011` | `/opt/reimbursement/ai-data/ai-review.sqlite3` |
| Receipt intelligence | `http://receipt-intelligence:8012` | `/opt/reimbursement/receipt-intelligence-data/receipt-intelligence.sqlite3` |
| Policy assistant | `http://policy-assistant:8013` | `/opt/reimbursement/policy-assistant-data/policy-assistant.sqlite3` |

Only the core API secret holds the outbound bearer tokens required to call
these services, plus the OAuth verifier metadata and allowlist bootstrap
configuration required by the core API. It also holds `AI_REVIEW_REFERENCE_HMAC_KEY` and
`POLICY_ASSISTANT_REFERENCE_HMAC_KEY`, private keys used only by the core
clients to keep pseudonymous references stable when their bearer tokens rotate.
Those keys are deliberately **not** in the AI-review or policy-assistant
runtime secrets. The advisory services' own secrets contain a distinct service
token and local path only. The host blocks all three advisory container
addresses from EC2 IMDS as defense in depth; the receipt/policy internal Docker
networks also provide no outbound route. Advisory services do not receive the
core `DATABASE_URL`, JWT secret, S3 configuration, or SMTP settings.

## Operations and recovery

- Use Session Manager or `deployment/scripts/restart-runtime.sh`, never SSH.
- Container logs live in `/presidio-reimburse-prod/{api,ai-review,receipt-intelligence,policy-assistant,proxy}`
  for 14 days by default.
- RDS has seven days of automated backups, deletion protection, and a final
  snapshot on destroy by default; the application database URL requires TLS.
- Each advisory SQLite file is distinct from core data and is not a workflow
  prerequisite. A host loss can lose advisory history/index data but cannot
  corrupt the reimbursement database or human decisions. Restore policy text
  through the administrator indexing endpoint after recovery; do not try to
  restore advisory SQLite data into the core database.
- The API must remain on one instance because startup runs Alembic migrations
  and the advisory services use single-process local SQLite stores. Scale-out
  needs AI-owned queues/datastores before adding replicas.

To intentionally destroy a non-production environment, first set
`rds_deletion_protection = false`, apply, and then destroy. The default still
creates a final snapshot; set `rds_skip_final_snapshot = true` only for a
disposable database. Keep `allow_bucket_force_destroy = false` for anything
with real receipts.

## Module map

```text
terraform/
  bootstrap/       encrypted, versioned state bucket
  modules/network/ VPC, subnets, security groups, S3 gateway endpoint
  modules/storage/ private upload and SPA buckets
  modules/registry/ ECR repositories and image retention
  modules/database/ private RDS PostgreSQL
  modules/credentials/ generated secrets container
  modules/app_config/ application runtime secret version
  modules/runtime/ EC2, EIP, IAM/SSM, Caddy + Docker templates
  modules/edge/ CloudFront, ACM, Route 53, private-bucket OAC
  modules/mail/ SES identity, DKIM, MAIL FROM DNS
  modules/logging/ CloudWatch container log groups
  modules/alerts/ CloudWatch alarms and SNS email topic
  modules/cost_guard/ AWS Budgets forecast and actual-spend alerts
```
