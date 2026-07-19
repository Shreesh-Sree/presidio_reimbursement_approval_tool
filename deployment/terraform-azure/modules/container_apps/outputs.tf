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

output "durable_worker_job_name" {
  description = "Scheduled Container Apps Job that processes durable outbox, email, and SLA work."
  value       = azurerm_container_app_job.durable_worker.name
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

output "backend_managed_identity_principal_id" {
  description = "Principal ID of the backend identity, including Blob data access."
  value       = azurerm_user_assigned_identity.backend.principal_id
}

output "advisory_managed_identity_principal_id" {
  description = "Principal ID shared by the internal advisory workloads."
  value       = azurerm_user_assigned_identity.advisory.principal_id
}
