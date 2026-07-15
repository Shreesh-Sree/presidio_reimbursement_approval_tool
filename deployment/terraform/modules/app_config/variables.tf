variable "application_secret_arn" {
  type = string
}

variable "ai_review_secret_arn" {
  type = string
}

variable "receipt_intelligence_secret_arn" {
  type = string
}

variable "policy_assistant_secret_arn" {
  type = string
}

variable "database_host" {
  type = string
}

variable "database_port" {
  type = number
}

variable "database_name" {
  type = string
}

variable "database_username" {
  type = string
}

variable "database_password" {
  type      = string
  sensitive = true
}

variable "jwt_secret" {
  type      = string
  sensitive = true
}

variable "ai_service_token" {
  type      = string
  sensitive = true
}

variable "ai_review_reference_hmac_key" {
  type      = string
  sensitive = true
}

variable "receipt_intelligence_service_token" {
  type      = string
  sensitive = true
}

variable "policy_assistant_service_token" {
  type      = string
  sensitive = true
}

variable "policy_assistant_reference_hmac_key" {
  type      = string
  sensitive = true
}

variable "aws_region" {
  type = string
}

variable "uploads_bucket_name" {
  type = string
}

variable "app_domain" {
  type = string
}

variable "smtp_host" {
  type = string
}

variable "smtp_from" {
  type = string
}

variable "email_delivery_enabled" {
  type = bool
}

variable "smtp_username" {
  type      = string
  default   = null
  nullable  = true
  sensitive = true
}

variable "smtp_password" {
  type      = string
  default   = null
  nullable  = true
  sensitive = true
}

variable "gemini_api_key" {
  type      = string
  default   = null
  nullable  = true
  sensitive = true
}

variable "groq_api_key" {
  type      = string
  default   = null
  nullable  = true
  sensitive = true
}

variable "ai_review_provider" {
  type = string
}

variable "groq_model" {
  type = string
}

variable "clerk_jwks_url" {
  type = string
}

variable "clerk_issuer" {
  type = string
}

variable "clerk_audience" {
  type = string
}

variable "clerk_authorized_parties" {
  type = list(string)
}

variable "super_admin_email" {
  type      = string
  sensitive = true
}

variable "default_organization_name" {
  type = string
}

variable "default_organization_code" {
  type = string
}

variable "default_department_name" {
  type = string
}

variable "default_department_code" {
  type = string
}
