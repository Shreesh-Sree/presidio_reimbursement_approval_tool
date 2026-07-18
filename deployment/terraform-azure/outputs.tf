output "resource_group_name" {
  description = "Resource group containing all deployed resources."
  value       = data.azurerm_resource_group.main.name
}

output "acr_login_server" {
  description = "Azure Container Registry login server URL."
  value       = module.registry.login_server
}

output "backend_fqdn" {
  description = "Public FQDN for the backend Container App."
  value       = module.container_apps.backend_fqdn
}

output "backend_url" {
  description = "Full HTTPS URL for the backend API."
  value       = "https://${module.container_apps.backend_fqdn}"
}

output "key_vault_name" {
  description = "Key Vault name for managing secrets."
  value       = module.keyvault.name
}

output "key_vault_uri" {
  description = "Key Vault URI."
  value       = module.keyvault.vault_uri
}

output "storage_account_name" {
  description = "Storage account name for blob uploads."
  value       = module.storage.account_name
}

output "uploads_container_name" {
  description = "Blob container name for file uploads."
  value       = module.storage.container_name
}

output "log_analytics_workspace_name" {
  description = "Log Analytics workspace name for centralized logging."
  value       = module.logging.workspace_name
}

output "container_apps_environment_name" {
  description = "Container Apps Environment name."
  value       = module.container_apps.environment_name
}
