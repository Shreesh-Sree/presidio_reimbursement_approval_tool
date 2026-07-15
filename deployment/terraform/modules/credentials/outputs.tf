output "application_secret_arn" {
  value = aws_secretsmanager_secret.application.arn
}

output "ai_review_secret_arn" {
  value = aws_secretsmanager_secret.ai_review.arn
}

output "receipt_intelligence_secret_arn" {
  value = aws_secretsmanager_secret.receipt_intelligence.arn
}

output "policy_assistant_secret_arn" {
  value = aws_secretsmanager_secret.policy_assistant.arn
}

output "database_password" {
  value     = random_password.database.result
  sensitive = true
}

output "jwt_secret" {
  value     = random_password.jwt.result
  sensitive = true
}

output "ai_service_token" {
  value     = random_password.ai_service.result
  sensitive = true
}

output "ai_review_reference_hmac_key" {
  value     = random_password.ai_review_reference_hmac.result
  sensitive = true
}

output "receipt_intelligence_service_token" {
  value     = random_password.receipt_intelligence_service.result
  sensitive = true
}

output "policy_assistant_service_token" {
  value     = random_password.policy_assistant_service.result
  sensitive = true
}

output "policy_assistant_reference_hmac_key" {
  value     = random_password.policy_assistant_reference_hmac.result
  sensitive = true
}
