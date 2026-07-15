resource "aws_cloudwatch_log_group" "api" {
  name              = "/${var.name_prefix}/api"
  retention_in_days = var.retention_in_days

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-api-logs"
    Service = "reimbursement-api"
  })
}

resource "aws_cloudwatch_log_group" "ai_review" {
  name              = "/${var.name_prefix}/ai-review"
  retention_in_days = var.retention_in_days

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-ai-review-logs"
    Service = "advisory-ai-review"
  })
}

resource "aws_cloudwatch_log_group" "proxy" {
  name              = "/${var.name_prefix}/proxy"
  retention_in_days = var.retention_in_days

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-proxy-logs"
    Service = "edge-proxy"
  })
}

# RDS creates these named export groups when PostgreSQL log exports are enabled.
# Owning them here applies the same bounded retention policy as container logs.
resource "aws_cloudwatch_log_group" "rds_postgresql" {
  name              = "/aws/rds/instance/${var.name_prefix}-postgres/postgresql"
  retention_in_days = var.retention_in_days

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-postgresql-logs"
    Service = "postgresql"
  })
}

resource "aws_cloudwatch_log_group" "rds_upgrade" {
  name              = "/aws/rds/instance/${var.name_prefix}-postgres/upgrade"
  retention_in_days = var.retention_in_days

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-postgres-upgrade-logs"
    Service = "postgresql"
  })
}
