output "environment_name" {
  description = "Container Apps Environment name."
  value       = azurerm_container_app_environment.main.name
}

output "environment_id" {
  description = "Container Apps Environment ID."
  value       = azurerm_container_app_environment.main.id
}

output "backend_fqdn" {
  description = "Backend Container App public FQDN."
  value       = azurerm_container_app.backend.ingress[0].fqdn
}

output "ai_review_fqdn" {
  description = "AI Review Container App internal FQDN."
  value       = azurerm_container_app.ai_review.ingress[0].fqdn
}

output "receipt_intelligence_fqdn" {
  description = "Receipt Intelligence Container App internal FQDN."
  value       = azurerm_container_app.receipt_intelligence.ingress[0].fqdn
}

output "policy_assistant_fqdn" {
  description = "Policy Assistant Container App internal FQDN."
  value       = azurerm_container_app.policy_assistant.ingress[0].fqdn
}

output "managed_identity_principal_id" {
  description = "Principal ID of the shared managed identity."
  value       = azurerm_user_assigned_identity.container_apps.principal_id
}
