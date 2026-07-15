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

output "registry_url" {
  value = split("/", aws_ecr_repository.api.repository_url)[0]
}
