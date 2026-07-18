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

output "primary_blob_endpoint" {
  description = "Primary blob service endpoint URL."
  value       = azurerm_storage_account.main.primary_blob_endpoint
}
