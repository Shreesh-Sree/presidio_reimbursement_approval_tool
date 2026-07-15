output "frontend_url" {
  description = "Public CloudFront URL for the React application."
  value       = "https://${local.app_domain}"
}

output "api_base_url" {
  description = "Vite API base URL. The frontend deployment script consumes this value."
  value       = "https://${local.api_domain}/api"
}

output "api_health_url" {
  description = "Public FastAPI health endpoint."
  value       = "https://${local.api_domain}/api/health"
}

output "runtime_instance_id" {
  description = "EC2 instance ID used by the SSM deployment helper."
  value       = module.runtime.instance_id
}

output "backend_ecr_repository_url" {
  description = "Private ECR repository for the FastAPI image."
  value       = module.registry.api_repository_url
}

output "ai_review_ecr_repository_url" {
  description = "Private ECR repository for the separate AI review service image."
  value       = module.registry.ai_repository_url
}

output "receipt_intelligence_ecr_repository_url" {
  description = "Private ECR repository for the isolated receipt intelligence image."
  value       = module.registry.receipt_intelligence_repository_url
}

output "policy_assistant_ecr_repository_url" {
  description = "Private ECR repository for the isolated policy assistant image."
  value       = module.registry.policy_assistant_repository_url
}

output "frontend_bucket_name" {
  description = "Private S3 bucket for compiled React assets."
  value       = module.storage.static_bucket_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID used for invalidations after frontend releases."
  value       = module.edge.distribution_id
}

output "uploads_bucket_name" {
  description = "Private S3 bucket used by the backend for policy documents and receipts."
  value       = module.storage.uploads_bucket_name
}

output "ses_identity_verification_token" {
  description = "SES verification is managed through Route 53; this is exposed only for troubleshooting."
  value       = module.mail.identity_verification_token
}
