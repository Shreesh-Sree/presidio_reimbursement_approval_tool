output "api_repository_url" {
  value = aws_ecr_repository.api.repository_url
}

output "api_repository_arn" {
  value = aws_ecr_repository.api.arn
}

output "ai_repository_url" {
  value = aws_ecr_repository.ai_review.repository_url
}

output "ai_repository_arn" {
  value = aws_ecr_repository.ai_review.arn
}

output "receipt_intelligence_repository_url" {
  value = aws_ecr_repository.receipt_intelligence.repository_url
}

output "receipt_intelligence_repository_arn" {
  value = aws_ecr_repository.receipt_intelligence.arn
}

output "policy_assistant_repository_url" {
  value = aws_ecr_repository.policy_assistant.repository_url
}

output "policy_assistant_repository_arn" {
  value = aws_ecr_repository.policy_assistant.arn
}

output "registry_url" {
  value = split("/", aws_ecr_repository.api.repository_url)[0]
}
