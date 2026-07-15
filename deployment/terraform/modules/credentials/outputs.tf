output "application_secret_arn" {
  value = aws_secretsmanager_secret.application.arn
}

output "ai_review_secret_arn" {
  value = aws_secretsmanager_secret.ai_review.arn
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
