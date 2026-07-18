variable "name_prefix" {
  description = "Resource naming prefix."
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name."
  type        = string
}

variable "location" {
  description = "Azure region."
  type        = string
}

variable "tags" {
  description = "Resource tags."
  type        = map(string)
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics workspace resource ID."
  type        = string
}

variable "log_analytics_workspace_primary_key" {
  description = "Log Analytics workspace primary shared key."
  type        = string
  sensitive   = true
}

variable "acr_login_server" {
  description = "ACR login server hostname."
  type        = string
}

variable "acr_id" {
  description = "ACR resource ID for role assignment."
  type        = string
}

variable "key_vault_id" {
  description = "Key Vault resource ID for role assignment."
  type        = string
}

variable "key_vault_uri" {
  description = "Key Vault URI."
  type        = string
}

# Image tags
variable "backend_image_tag" {
  description = "Docker image tag for the backend service."
  type        = string
}

variable "ai_review_image_tag" {
  description = "Docker image tag for the AI review service."
  type        = string
}

variable "receipt_intelligence_image_tag" {
  description = "Docker image tag for the receipt intelligence service."
  type        = string
}

variable "policy_assistant_image_tag" {
  description = "Docker image tag for the policy assistant service."
  type        = string
}

# Non-secret env vars
variable "supabase_url" {
  description = "Supabase project URL."
  type        = string
}

variable "cors_origins" {
  description = "Allowed CORS origins."
  type        = string
}

# Key Vault secret URIs
variable "database_url_secret_uri" {
  description = "Key Vault secret URI for DATABASE_URL."
  type        = string
}

variable "jwt_secret_secret_uri" {
  description = "Key Vault secret URI for JWT_SECRET."
  type        = string
}

variable "supabase_jwt_secret_secret_uri" {
  description = "Key Vault secret URI for SUPABASE_JWT_SECRET."
  type        = string
}

variable "supabase_service_role_key_secret_uri" {
  description = "Key Vault secret URI for SUPABASE_SERVICE_ROLE_KEY."
  type        = string
}

variable "super_admin_email_secret_uri" {
  description = "Key Vault secret URI for SUPER_ADMIN_EMAIL."
  type        = string
}

variable "ai_review_service_token_secret_uri" {
  description = "Key Vault secret URI for AI_REVIEW_SERVICE_TOKEN."
  type        = string
}

variable "ai_review_reference_hmac_key_secret_uri" {
  description = "Key Vault secret URI for AI_REVIEW_REFERENCE_HMAC_KEY."
  type        = string
}

variable "receipt_intelligence_token_secret_uri" {
  description = "Key Vault secret URI for RECEIPT_INTELLIGENCE_SERVICE_TOKEN."
  type        = string
}

variable "policy_assistant_token_secret_uri" {
  description = "Key Vault secret URI for POLICY_ASSISTANT_SERVICE_TOKEN."
  type        = string
}

variable "policy_assistant_hmac_key_secret_uri" {
  description = "Key Vault secret URI for POLICY_ASSISTANT_REFERENCE_HMAC_KEY."
  type        = string
}
