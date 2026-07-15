output "version_id" {
  value = aws_secretsmanager_secret_version.application.version_id
}

output "ai_review_version_id" {
  value = aws_secretsmanager_secret_version.ai_review.version_id
}
