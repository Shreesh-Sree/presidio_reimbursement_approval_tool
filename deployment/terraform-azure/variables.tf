variable "subscription_id" {
  description = "Azure subscription ID. Set through the protected deployment environment."
  type        = string
}

variable "resource_group_name" {
  description = "Name of the pre-existing Azure resource group."
  type        = string
  default     = "presidio-reimbursement-rg"
}

variable "location" {
  description = "Azure region for all resources."
  type        = string
  default     = "centralindia"
}

variable "network_address_space" {
  description = "Private address space reserved for Container Apps egress and private endpoints. Choose a non-overlapping production CIDR before first apply."
  type        = string
  default     = "10.42.0.0/16"

  validation {
    condition     = can(cidrnetmask(var.network_address_space))
    error_message = "network_address_space must be a valid CIDR block."
  }
}

variable "container_apps_subnet_address_prefix" {
  description = "Dedicated undelegated /23-or-larger subnet for the Consumption Container Apps environment. Changing it recreates the environment."
  type        = string
  default     = "10.42.0.0/23"

  validation {
    condition     = can(cidrnetmask(var.container_apps_subnet_address_prefix))
    error_message = "container_apps_subnet_address_prefix must be a valid CIDR block."
  }
}

variable "private_endpoints_subnet_address_prefix" {
  description = "Dedicated private-endpoint subnet. Size it for the registry, Blob, Key Vault, and future endpoint growth."
  type        = string
  default     = "10.42.2.0/24"

  validation {
    condition     = can(cidrnetmask(var.private_endpoints_subnet_address_prefix))
    error_message = "private_endpoints_subnet_address_prefix must be a valid CIDR block."
  }
}

variable "project_name" {
  description = "Lowercase slug used in Azure resource names."
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

# --- Secrets (all sensitive, no defaults) ---

variable "database_url" {
  description = "Supabase PostgreSQL connection string."
  type        = string
  sensitive   = true
}

variable "jwt_secret" {
  description = "JWT signing secret for the backend API."
  type        = string
  sensitive   = true
}

variable "supabase_url" {
  description = "Supabase project URL (https://<ref>.supabase.co)."
  type        = string
}

variable "supabase_jwt_secret" {
  description = "Supabase JWT secret for token verification."
  type        = string
  sensitive   = true
}

variable "supabase_service_role_key" {
  description = "Supabase service role key for admin operations."
  type        = string
  sensitive   = true
}

variable "super_admin_email" {
  description = "Email for the initial super admin user."
  type        = string
  sensitive   = true
}

variable "key_vault_secret_expiration_date" {
  description = "Required ISO-8601 UTC rotation deadline for managed Key Vault secret versions. Rotate values before this date; do not use a moving timestamp expression."
  type        = string

  validation {
    condition     = can(formatdate("YYYY-MM-DD'T'hh:mm:ss'Z'", var.key_vault_secret_expiration_date))
    error_message = "key_vault_secret_expiration_date must be an ISO-8601 UTC timestamp, for example 2027-01-31T00:00:00Z."
  }
}

variable "storage_cmk_key_expiration_date" {
  description = "Required ISO-8601 UTC rotation deadline for the Storage customer-managed key."
  type        = string

  validation {
    condition     = can(formatdate("YYYY-MM-DD'T'hh:mm:ss'Z'", var.storage_cmk_key_expiration_date))
    error_message = "storage_cmk_key_expiration_date must be an ISO-8601 UTC timestamp, for example 2027-01-31T00:00:00Z."
  }
}

variable "email_delivery_enabled" {
  description = "Whether the durable worker may send transactional email in this environment."
  type        = bool
  default     = true
}

variable "azure_communication_connection_string" {
  description = "Azure Communication Services connection string for durable transactional email delivery."
  type        = string
  sensitive   = true

  validation {
    condition     = !var.email_delivery_enabled || trimspace(var.azure_communication_connection_string) != ""
    error_message = "azure_communication_connection_string must be non-empty when email_delivery_enabled is true."
  }
}

variable "azure_communication_sender" {
  description = "Verified Azure Communication Services sender address."
  type        = string

  validation {
    condition     = !var.email_delivery_enabled || can(regex("^[^@[:space:]]+@[^@[:space:]]+\\.[^@[:space:]]+$", trimspace(var.azure_communication_sender)))
    error_message = "azure_communication_sender must be a non-empty verified email address when email_delivery_enabled is true."
  }
}

variable "ai_review_service_token" {
  description = "Bearer token for authenticating with the AI review service."
  type        = string
  sensitive   = true
}

variable "ai_review_database_url" {
  description = "Dedicated PostgreSQL URL for durable AI review jobs."
  type        = string
  sensitive   = true
}

variable "ai_review_reference_hmac_key" {
  description = "HMAC key for AI review reference integrity."
  type        = string
  sensitive   = true
}

variable "receipt_intelligence_service_token" {
  description = "Bearer token for authenticating with the receipt intelligence service."
  type        = string
  sensitive   = true
}

variable "receipt_intelligence_database_url" {
  description = "Dedicated PostgreSQL URL for durable receipt digest observations."
  type        = string
  sensitive   = true
}

variable "policy_assistant_service_token" {
  description = "Bearer token for authenticating with the policy assistant service."
  type        = string
  sensitive   = true
}

variable "policy_assistant_database_url" {
  description = "Dedicated PostgreSQL URL for durable policy-assistant indexes."
  type        = string
  sensitive   = true
}

variable "policy_assistant_reference_hmac_key" {
  description = "HMAC key for policy assistant reference integrity."
  type        = string
  sensitive   = true
}

# --- Application config ---

variable "cors_origins" {
  description = "Comma-separated explicit allowed CORS origins for the backend API."
  type        = string

  validation {
    condition = trimspace(var.cors_origins) != "" && !contains(
      [for origin in split(",", var.cors_origins) : trimspace(origin)],
      "*",
      ) && alltrue([
        for origin in split(",", var.cors_origins) : can(regex("^https?://[^/]+$", trimspace(origin)))
    ])
    error_message = "cors_origins must contain one or more explicit origin-only http(s) URLs and must never include '*'."
  }
}

variable "backend_image_digest" {
  description = "Immutable OCI digest for the backend image, for example sha256:<64 lowercase hex characters>."
  type        = string

  validation {
    condition     = can(regex("^sha256:[a-f0-9]{64}$", var.backend_image_digest))
    error_message = "backend_image_digest must be an immutable sha256 digest."
  }
}

variable "ai_review_image_digest" {
  description = "Immutable OCI digest for the AI review image."
  type        = string

  validation {
    condition     = can(regex("^sha256:[a-f0-9]{64}$", var.ai_review_image_digest))
    error_message = "ai_review_image_digest must be an immutable sha256 digest."
  }
}

variable "receipt_intelligence_image_digest" {
  description = "Immutable OCI digest for the receipt intelligence image."
  type        = string

  validation {
    condition     = can(regex("^sha256:[a-f0-9]{64}$", var.receipt_intelligence_image_digest))
    error_message = "receipt_intelligence_image_digest must be an immutable sha256 digest."
  }
}

variable "policy_assistant_image_digest" {
  description = "Immutable OCI digest for the policy assistant image."
  type        = string

  validation {
    condition     = can(regex("^sha256:[a-f0-9]{64}$", var.policy_assistant_image_digest))
    error_message = "policy_assistant_image_digest must be an immutable sha256 digest."
  }
}

variable "log_retention_days" {
  description = "Log Analytics workspace retention in days."
  type        = number
  default     = 30

  validation {
    condition     = var.log_retention_days >= 30 && var.log_retention_days <= 730
    error_message = "log_retention_days must be between 30 and 730."
  }
}

variable "owner" {
  description = "Operational owner used for Azure resource tagging and alert routing."
  type        = string
  default     = "platform"
}

variable "cost_center" {
  description = "Cost allocation value used for Azure resource tagging."
  type        = string
  default     = "reimbursement"
}

variable "data_classification" {
  description = "Data classification tag for resources that process reimbursement records."
  type        = string
  default     = "confidential"
}

variable "alert_email" {
  description = "Operational mailbox or paging-email endpoint for production alert routing."
  type        = string

  validation {
    condition     = can(regex("^[^@[:space:]]+@[^@[:space:]]+\\.[^@[:space:]]+$", var.alert_email))
    error_message = "alert_email must be a valid operational email address."
  }
}
