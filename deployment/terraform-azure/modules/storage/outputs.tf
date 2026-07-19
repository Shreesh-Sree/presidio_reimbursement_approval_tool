output "account_name" {
  description = "Storage account name."
  value       = azurerm_storage_account.main.name
}

output "account_id" {
  description = "Storage account resource ID."
  value       = azurerm_storage_account.main.id
}

output "container_name" {
  description = "Blob container name for uploads."
  value       = azurerm_storage_container.uploads.name
}

output "container_resource_manager_id" {
  description = "Azure Resource Manager ID for the uploads container, suitable for data-plane RBAC scope."
  value       = "${azurerm_storage_account.main.id}/blobServices/default/containers/${azurerm_storage_container.uploads.name}"
}

output "primary_blob_endpoint" {
  description = "Primary blob service endpoint URL."
  value       = azurerm_storage_account.main.primary_blob_endpoint
}
