variable "subscription_id" {
  description = "Azure subscription ID."
  type        = string
  default     = "c3e6aac4-093d-43cc-aa74-a67be077f958"
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

variable "ai_review_service_token" {
  description = "Bearer token for authenticating with the AI review service."
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

variable "policy_assistant_service_token" {
  description = "Bearer token for authenticating with the policy assistant service."
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
  description = "Comma-separated allowed CORS origins for the backend API."
  type        = string
  default     = "*"
}

variable "backend_image_tag" {
  description = "Docker image tag for the backend service."
  type        = string
  default     = "latest"
}

variable "ai_review_image_tag" {
  description = "Docker image tag for the AI review service."
  type        = string
  default     = "latest"
}

variable "receipt_intelligence_image_tag" {
  description = "Docker image tag for the receipt intelligence service."
  type        = string
  default     = "latest"
}

variable "policy_assistant_image_tag" {
  description = "Docker image tag for the policy assistant service."
  type        = string
  default     = "latest"
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
