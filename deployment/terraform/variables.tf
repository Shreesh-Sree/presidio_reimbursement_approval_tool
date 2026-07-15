variable "aws_region" {
  description = "AWS region for the workload. us-east-1 is the cost-oriented default."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Lowercase slug used in AWS resource names."
  type        = string
  default     = "presidio-reimburse"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,24}$", var.project_name))
    error_message = "project_name must be a 3-25 character lowercase slug."
  }
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "prod"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,14}$", var.environment))
    error_message = "environment must be a 2-15 character lowercase slug."
  }
}

variable "domain_name" {
  description = "Existing root domain managed by the Route 53 hosted zone, for example example.com."
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z0-9][A-Za-z0-9.-]+[A-Za-z0-9]$", var.domain_name))
    error_message = "domain_name must be a valid DNS name without a protocol or path."
  }
}

variable "route53_zone_id" {
  description = "Hosted-zone ID for domain_name. The zone must already exist."
  type        = string
}

variable "acme_email" {
  description = "Email address used by Caddy/Let's Encrypt for API certificate notices."
  type        = string

  validation {
    condition     = can(regex("^[^@[:space:]]+@[^@[:space:]]+\\.[^@[:space:]]+$", var.acme_email))
    error_message = "acme_email must be a valid email address."
  }
}

variable "budget_alert_email" {
  description = "Recipient for AWS Budgets and operational SNS alerts."
  type        = string

  validation {
    condition     = can(regex("^[^@[:space:]]+@[^@[:space:]]+\\.[^@[:space:]]+$", var.budget_alert_email))
    error_message = "budget_alert_email must be a valid email address."
  }
}

variable "cost_center" {
  description = "Cost allocation tag value."
  type        = string
  default     = "reimbursement"
}

variable "vpc_cidr" {
  description = "CIDR block for the deployment VPC."
  type        = string
  default     = "10.42.0.0/16"
}

variable "allowed_ingress_cidr" {
  description = "CIDR allowed to reach the public API. Keep 0.0.0.0/0 for a public web application."
  type        = string
  default     = "0.0.0.0/0"
}

variable "ec2_instance_type" {
  description = "Cost/performance starting point for the API and separate advisory AI container."
  type        = string
  default     = "t3a.small"
}

variable "ec2_root_volume_gib" {
  description = "Encrypted gp3 root volume size for the runtime host."
  type        = number
  default     = 20

  validation {
    condition     = var.ec2_root_volume_gib >= 16 && var.ec2_root_volume_gib <= 100
    error_message = "ec2_root_volume_gib must be between 16 and 100 GiB for this budget profile."
  }
}

variable "postgres_instance_class" {
  description = "Single-AZ RDS PostgreSQL instance class."
  type        = string
  default     = "db.t4g.micro"
}

variable "postgres_allocated_storage_gib" {
  description = "Initial encrypted RDS gp3 storage allocation."
  type        = number
  default     = 20
}

variable "postgres_max_allocated_storage_gib" {
  description = "Autoscaling ceiling for RDS storage; constrains surprise storage cost."
  type        = number
  default     = 40
}

variable "postgres_engine_version" {
  description = "Optional PostgreSQL engine version. Leave null to use the region's current supported default."
  type        = string
  default     = null
  nullable    = true
}

variable "enable_email_delivery" {
  description = "Enable SMTP status emails after SES identity verification and SMTP credentials are supplied."
  type        = bool
  default     = false
}

variable "ses_smtp_username" {
  description = "Optional SES SMTP username. Required only when enable_email_delivery is true."
  type        = string
  default     = null
  nullable    = true
  sensitive   = true
}

variable "ses_smtp_password" {
  description = "Optional SES SMTP password. Required only when enable_email_delivery is true."
  type        = string
  default     = null
  nullable    = true
  sensitive   = true
}

variable "gemini_api_key" {
  description = "Optional provider key used only by the isolated advisory AI service."
  type        = string
  default     = null
  nullable    = true
  sensitive   = true
}

variable "groq_api_key" {
  description = "Optional Groq provider key used only by the isolated advisory AI service. Keep it out of source control and CI logs."
  type        = string
  default     = null
  nullable    = true
  sensitive   = true
}

variable "ai_review_provider" {
  description = "Narrative provider for the isolated AI reviewer. rule_based has no external model dependency."
  type        = string
  default     = "rule_based"

  validation {
    condition     = contains(["rule_based", "gemini", "groq"], var.ai_review_provider)
    error_message = "ai_review_provider must be rule_based, gemini, or groq."
  }
}

variable "groq_model" {
  description = "Groq model identifier used when ai_review_provider is groq."
  type        = string
  default     = "openai/gpt-oss-20b"

  validation {
    condition     = length(trimspace(var.groq_model)) > 0 && length(trimspace(var.groq_model)) <= 255
    error_message = "groq_model must be a non-empty model identifier no longer than 255 characters."
  }
}

variable "clerk_publishable_key" {
  description = "Public Clerk publishable key embedded into the Vite build. This is intentionally not a secret."
  type        = string

  validation {
    condition     = can(regex("^pk_[A-Za-z0-9_-]+$", trimspace(var.clerk_publishable_key)))
    error_message = "clerk_publishable_key must be a Clerk publishable key beginning with pk_."
  }
}

variable "clerk_jwt_template" {
  description = "Name of the Clerk JWT template requested by the browser for API calls."
  type        = string
  default     = "presidio-api"

  validation {
    condition     = can(regex("^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$", trimspace(var.clerk_jwt_template)))
    error_message = "clerk_jwt_template must be a 1-64 character slug containing letters, numbers, hyphens, or underscores."
  }
}

variable "clerk_jwks_url" {
  description = "HTTPS JWKS endpoint for the Clerk JWT template. The API validates OAuth bearer tokens against this endpoint."
  type        = string

  validation {
    condition     = can(regex("^https://[^[:space:]]+$", trimspace(var.clerk_jwks_url)))
    error_message = "clerk_jwks_url must be an HTTPS URL."
  }
}

variable "clerk_issuer" {
  description = "Expected iss claim for Clerk JWTs. Copy the issuer from the Clerk JWT template configuration."
  type        = string

  validation {
    condition     = can(regex("^https://[^[:space:]]+$", trimspace(var.clerk_issuer)))
    error_message = "clerk_issuer must be an HTTPS URL."
  }
}

variable "clerk_audience" {
  description = "Expected aud claim for Clerk API JWTs. It must match the selected JWT template."
  type        = string

  validation {
    condition     = length(trimspace(var.clerk_audience)) > 0 && length(trimspace(var.clerk_audience)) <= 255
    error_message = "clerk_audience must be a non-empty value no longer than 255 characters."
  }
}

variable "clerk_authorized_parties" {
  description = "Allowed browser origins for the Clerk azp claim, such as the CloudFront application URL."
  type        = list(string)

  validation {
    condition = length(var.clerk_authorized_parties) > 0 && alltrue([
      for party in var.clerk_authorized_parties : can(regex("^https://[^[:space:]]+$", trimspace(party)))
    ])
    error_message = "clerk_authorized_parties must contain at least one HTTPS browser origin."
  }
}

variable "super_admin_email" {
  description = "Email allowed to bootstrap the first Clerk-authenticated Super Admin. Store the real value outside version control."
  type        = string
  sensitive   = true

  validation {
    condition     = can(regex("^[^@[:space:]]+@[^@[:space:]]+\\.[^@[:space:]]+$", trimspace(var.super_admin_email)))
    error_message = "super_admin_email must be a valid email address."
  }
}

variable "default_organization_name" {
  description = "Organization name used when the first Super Admin signs in and no organization exists."
  type        = string

  validation {
    condition     = length(trimspace(var.default_organization_name)) >= 1 && length(trimspace(var.default_organization_name)) <= 255
    error_message = "default_organization_name must be between 1 and 255 characters."
  }
}

variable "default_organization_code" {
  description = "Organization code used when the first Super Admin signs in and no organization exists."
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z0-9][A-Za-z0-9_-]{1,49}$", trimspace(var.default_organization_code)))
    error_message = "default_organization_code must be a 2-50 character code containing letters, numbers, hyphens, or underscores."
  }
}

variable "default_department_name" {
  description = "Department name used when the first Super Admin signs in and no department exists."
  type        = string

  validation {
    condition     = length(trimspace(var.default_department_name)) >= 1 && length(trimspace(var.default_department_name)) <= 255
    error_message = "default_department_name must be between 1 and 255 characters."
  }
}

variable "default_department_code" {
  description = "Department code used when the first Super Admin signs in and no department exists."
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z0-9][A-Za-z0-9_-]{1,49}$", trimspace(var.default_department_code)))
    error_message = "default_department_code must be a 2-50 character code containing letters, numbers, hyphens, or underscores."
  }
}

variable "monthly_budget_limit_usd" {
  description = "Monthly AWS budget cap. Alerts are warnings, not a billing hard-stop."
  type        = number
  default     = 75

  validation {
    condition     = var.monthly_budget_limit_usd > 0 && var.monthly_budget_limit_usd <= 75
    error_message = "monthly_budget_limit_usd must be greater than zero and cannot exceed the $75 cap."
  }
}

variable "log_retention_days" {
  description = "CloudWatch log retention to cap observability storage cost."
  type        = number
  default     = 14
}

variable "rds_deletion_protection" {
  description = "Protect the production database from accidental Terraform destruction."
  type        = bool
  default     = true
}

variable "rds_skip_final_snapshot" {
  description = "Skip the final RDS snapshot only for disposable environments."
  type        = bool
  default     = false
}

variable "allow_bucket_force_destroy" {
  description = "Allow deleting all objects during terraform destroy. Keep false for production."
  type        = bool
  default     = false
}
