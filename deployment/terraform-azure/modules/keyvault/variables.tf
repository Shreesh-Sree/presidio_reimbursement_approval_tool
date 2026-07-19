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

variable "tenant_id" {
  description = "Azure AD tenant ID."
  type        = string
}

variable "tags" {
  description = "Resource tags."
  type        = map(string)
}

variable "secrets" {
  description = "Map of secret names to their values."
  type        = map(string)
  sensitive   = true
}

variable "container_apps_subnet_id" {
  description = "Container Apps infrastructure subnet permitted by the vault firewall."
  type        = string
}

variable "private_endpoint_subnet_id" {
  description = "Dedicated subnet in which the Key Vault private endpoint is created."
  type        = string
}

variable "private_dns_zone_id" {
  description = "Private DNS zone ID for privatelink.vaultcore.azure.net."
  type        = string
}

variable "secret_expiration_date" {
  description = "ISO-8601 UTC expiry applied to managed Key Vault secret versions; rotate values before this date."
  type        = string
}

variable "storage_cmk_key_expiration_date" {
  description = "ISO-8601 UTC expiry for the Storage customer-managed encryption key."
  type        = string
}
