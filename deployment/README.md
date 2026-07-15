# AWS deployment

This folder deploys the complete reimbursement application as a deliberately
small AWS production/pilot footprint. It preserves the application's important
boundary: the FastAPI reimbursement service and the advisory AI reviewer run as
separate private containers, and the reviewer owns its own encrypted SQLite
datastore. The AI service has no database credentials for the reimbursement
system, cannot reach the EC2 metadata role endpoint, and is never exposed to
the public internet.

The target is **under USD 75/month in `us-east-1` for a small team and modest
traffic**. It is a single-host, Single-AZ cost profile, not an HA/SLA profile.
AWS Budgets alerts are included, but they are delayed notifications—not a hard
spending cutoff.

## Architecture

```text
Browser
  │
  ├─ HTTPS ──> CloudFront + ACM ──> private S3 bucket (React/Vite SPA)
  │                  │
  │                  └─ Route 53: app.<domain>
  │
  └─ HTTPS ──> Route 53: api.<domain> ──> Elastic IP ──> EC2 + Caddy
                                                              │ private Docker network
                                                              ├─ FastAPI API ──> RDS PostgreSQL
                                                              │       │              (private subnets)
                                                              │       ├─> private S3 uploads bucket
                                                              │       └─> AI-review HTTP service
                                                              └─ advisory AI review + its own SQLite volume

EC2 instance profile ──> ECR, Secrets Manager, S3, CloudWatch Logs, SSM
SES + Route 53 ──> verified sender / optional SMTP delivery
CloudWatch + SNS ──> operational alarms
AWS Budgets ──> $60 / $70 / $75 forecast and actual-spend alerts
```

## Services and why each is here

| AWS service | Purpose | Cost-conscious choice |
| --- | --- | --- |
| Amazon EC2 | Runs Caddy, FastAPI, and the separately isolated AI-review container. | One `t3a.small` host rather than two always-on container platforms. |
| Amazon RDS for PostgreSQL | Durable transactional reimbursement database. | `db.t4g.micro`, encrypted gp3, private, Single-AZ. |
| Amazon S3 | Private receipts/policy documents, private SPA assets, and Terraform state. | Lifecycle cleanup and no direct public access. |
| Amazon CloudFront + ACM | HTTPS SPA delivery and TLS certificate. | `PriceClass_100`, no paid WAF tier. |
| Amazon ECR | Versioned API and AI container images. | Scan on push; lifecycle keeps five images. |
| Amazon Route 53 | DNS for `app` and `api`, ACM DNS validation, SES records. | Uses an existing hosted zone. |
| AWS Secrets Manager | Separate core-runtime and AI-runtime secrets fetched by the EC2 role. | The AI secret excludes database, JWT, SMTP, and S3 credentials. |
| Amazon SES | Optional status-change email delivery. | Domain/DKIM setup only; SMTP delivery remains disabled by default. |
| Amazon CloudWatch + SNS | 14-day container logs and four capacity/storage alarms. | No high-resolution metrics, dashboards, or log archive. |
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
| Route 53 + Secrets Manager + four basic alarms | 2–3 |
| ECR, S3, CloudFront, CloudWatch logs, SES at modest traffic | 2–14 |
| **Expected total** | **36–55** |

That leaves roughly $20 of headroom for normal variation. Traffic, unusually
large uploads, CloudFront egress, a resize, or optional Gemini/provider usage
can still exceed the cap. The root module creates forecast **and actual-spend**
alerts at 80%, about 93%, and 100% of the configured limit (USD 60/70/75 at
the default). Confirm
both the AWS Budgets and SNS subscription emails after the first apply.

Pricing references: [RDS for PostgreSQL](https://aws.amazon.com/rds/postgresql/pricing/),
[public IPv4](https://aws.amazon.com/vpc/pricing/),
[AWS Budgets](https://aws.amazon.com/aws-cost-management/aws-budgets/pricing/),
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

## First deployment

Terraform state contains generated database, JWT, and service-to-service
secrets. **Create encrypted remote state before applying the main stack.**

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
   # Edit both files: use the state bucket output, your domain/zone IDs,
   # ACME address, and budget-alert email.
   terraform init -backend-config=backend.hcl
   terraform plan -out=tfplan
   terraform apply tfplan
   ```

   The EC2 runtime service retries image pulls every minute until the first
   images exist. CloudFront and ACM can take several minutes to finish.

3. Build and publish the two images, then start the private runtime with SSM.

   ```bash
   export AWS_REGION=us-east-1
   DEPLOY_RUNTIME=1 bash deployment/scripts/build-and-push.sh
   ```

4. Build the SPA with the Terraform-provided API URL, upload it to its private
   bucket, and invalidate CloudFront.

   ```bash
   export AWS_REGION=us-east-1
   bash deployment/scripts/deploy-frontend.sh
   ```

5. Verify DNS/TLS and bootstrap the first administrator in the UI.

   ```bash
   curl "$(terraform -chdir=deployment/terraform output -raw api_health_url)"
   ```

For later backend/AI releases, publish the deliberately mutable `stable` tag
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

The AI reviewer is deterministic and fully functional without a model key.
`gemini_api_key` is optional and is stored only in the runtime secret; it is
read only by the separate AI-review container. Any third-party AI usage is
outside the AWS USD 75 budget and should have its own vendor-side limit.

## Operations and recovery

- Use Session Manager or `deployment/scripts/restart-runtime.sh`, never SSH.
- Container logs live in `/presidio-reimburse-prod/{api,ai-review,proxy}` for
  14 days by default.
- RDS has seven days of automated backups, deletion protection, and a final
  snapshot on destroy by default; the application database URL requires TLS.
- The AI SQLite file is distinct from core data at
  `/opt/reimbursement/ai-data/ai-review.sqlite3`; it is advisory audit data,
  not a workflow prerequisite. A host loss can lose that advisory history but
  cannot corrupt the reimbursement database or decisions.
- The API must remain on one instance because startup runs Alembic migrations
  and the AI service's default SQLite worker is single-process. Scale-out needs
  an AI-owned queue/database before adding replicas.

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
