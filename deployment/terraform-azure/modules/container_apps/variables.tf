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

variable "infrastructure_subnet_id" {
  description = "Dedicated, undelegated Consumption Container Apps infrastructure subnet. Changing it recreates the environment."
  type        = string
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

variable "service_contract" {
  description = "Authoritative repository and port contract shared with the release workflow."
  type = object({
    backend              = object({ repository = string, port = number })
    ai_review            = object({ repository = string, port = number })
    receipt_intelligence = object({ repository = string, port = number })
    policy_assistant     = object({ repository = string, port = number })
  })
}

variable "backend_image_digest" {
  description = "Immutable OCI digest for the backend image."
  type        = string
}

variable "ai_review_image_digest" {
  description = "Immutable OCI digest for the AI review image."
  type        = string
}

variable "receipt_intelligence_image_digest" {
  description = "Immutable OCI digest for the receipt intelligence image."
  type        = string
}

variable "policy_assistant_image_digest" {
  description = "Immutable OCI digest for the policy assistant image."
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

variable "email_delivery_enabled" {
  description = "Whether the API and scheduled worker may deliver transactional email."
  type        = bool
}

variable "azure_communication_sender" {
  description = "Verified sender address for Azure Communication Services email."
  type        = string
}

variable "storage_account_url" {
  description = "Blob service endpoint used by the backend with managed identity."
  type        = string
}

variable "storage_container_name" {
  description = "Private Azure Blob container used for attachment bytes."
  type        = string
}

variable "storage_container_resource_manager_id" {
  description = "Resource Manager ID used to scope Storage Blob Data Contributor to the backend identity."
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

variable "azure_communication_connection_string_secret_uri" {
  description = "Key Vault secret URI for AZURE_COMMUNICATION_CONNECTION_STRING."
  type        = string
}

variable "ai_review_service_token_secret_uri" {
  description = "Key Vault secret URI for AI_REVIEW_SERVICE_TOKEN."
  type        = string
}

variable "ai_review_database_url_secret_uri" {
  description = "Key Vault secret URI for AI_REVIEW_DATABASE_URL."
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

variable "receipt_intelligence_database_url_secret_uri" {
  description = "Key Vault secret URI for RECEIPT_INTELLIGENCE_DATABASE_URL."
  type        = string
}

variable "policy_assistant_token_secret_uri" {
  description = "Key Vault secret URI for POLICY_ASSISTANT_SERVICE_TOKEN."
  type        = string
}

variable "policy_assistant_database_url_secret_uri" {
  description = "Key Vault secret URI for POLICY_ASSISTANT_DATABASE_URL."
  type        = string
}

variable "policy_assistant_hmac_key_secret_uri" {
  description = "Key Vault secret URI for POLICY_ASSISTANT_REFERENCE_HMAC_KEY."
  type        = string
}
