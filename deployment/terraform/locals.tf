locals {
  name_prefix = "${var.project_name}-${var.environment}"
  app_domain  = "app.${var.domain_name}"
  api_domain  = "api.${var.domain_name}"

  # RDS requires subnets in at least two AZs. The application and primary DB
  # are deliberately placed in the first AZ to avoid cross-AZ transfer cost.
  availability_zones = slice(data.aws_availability_zones.available.names, 0, 2)

  common_tags = {
    Application = "presidio-reimbursement"
    Environment = var.environment
    ManagedBy   = "terraform"
    CostCenter  = var.cost_center
  }
}
