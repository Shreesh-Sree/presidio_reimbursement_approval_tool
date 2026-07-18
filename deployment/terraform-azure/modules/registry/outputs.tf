output "id" {
  description = "ACR resource ID."
  value       = azurerm_container_registry.main.id
}

output "login_server" {
  description = "ACR login server hostname."
  value       = azurerm_container_registry.main.login_server
}

output "name" {
  description = "ACR name."
  value       = azurerm_container_registry.main.name
}
