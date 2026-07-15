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

output "receipt_intelligence_log_group_name" {
  value = aws_cloudwatch_log_group.receipt_intelligence.name
}

output "receipt_intelligence_log_group_arn" {
  value = aws_cloudwatch_log_group.receipt_intelligence.arn
}

output "policy_assistant_log_group_name" {
  value = aws_cloudwatch_log_group.policy_assistant.name
}

output "policy_assistant_log_group_arn" {
  value = aws_cloudwatch_log_group.policy_assistant.arn
}

output "proxy_log_group_name" {
  value = aws_cloudwatch_log_group.proxy.name
}

output "proxy_log_group_arn" {
  value = aws_cloudwatch_log_group.proxy.arn
}
