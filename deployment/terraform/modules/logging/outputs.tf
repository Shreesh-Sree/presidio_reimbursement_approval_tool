output "api_log_group_name" {
  value = aws_cloudwatch_log_group.api.name
}

output "api_log_group_arn" {
  value = aws_cloudwatch_log_group.api.arn
}

output "ai_log_group_name" {
  value = aws_cloudwatch_log_group.ai_review.name
}

output "ai_log_group_arn" {
  value = aws_cloudwatch_log_group.ai_review.arn
}

output "proxy_log_group_name" {
  value = aws_cloudwatch_log_group.proxy.name
}

output "proxy_log_group_arn" {
  value = aws_cloudwatch_log_group.proxy.arn
}
