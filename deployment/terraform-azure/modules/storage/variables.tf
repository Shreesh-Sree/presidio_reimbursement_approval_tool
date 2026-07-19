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

variable "container_apps_subnet_id" {
  description = "Container Apps infrastructure subnet permitted by the Storage firewall."
  type        = string
}

variable "private_endpoint_subnet_id" {
  description = "Dedicated subnet in which the Blob private endpoint is created."
  type        = string
}

variable "private_dns_zone_id" {
  description = "Private DNS zone ID for privatelink.blob.core.windows.net."
  type        = string
}

variable "key_vault_id" {
  description = "Key Vault scope used to grant the Storage encryption identity crypto permissions."
  type        = string
}

variable "customer_managed_key_id" {
  description = "Versionless Key Vault key ID used for Storage customer-managed encryption."
  type        = string
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics workspace receiving modern Blob read/write/delete diagnostics."
  type        = string
}
