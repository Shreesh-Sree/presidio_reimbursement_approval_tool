output "id" {
  description = "Key Vault resource ID."
  value       = azurerm_key_vault.main.id
}

output "name" {
  description = "Key Vault name."
  value       = azurerm_key_vault.main.name
}

output "vault_uri" {
  description = "Key Vault URI."
  value       = azurerm_key_vault.main.vault_uri
}

output "secret_uris" {
  description = "Map of secret name to versionless secret URI."
  value = {
    for k, v in azurerm_key_vault_secret.secrets : k => v.versionless_id
  }
}

output "storage_cmk_key_name" {
  description = "Name of the Key Vault key used by the Storage account customer-managed key binding."
  value       = azurerm_key_vault_key.storage_cmk.name
}

output "storage_cmk_key_id" {
  description = "Versionless Key Vault key ID used by Azure Storage encryption."
  value       = azurerm_key_vault_key.storage_cmk.versionless_id
}
