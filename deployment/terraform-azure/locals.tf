locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = {
    project             = var.project_name
    environment         = var.environment
    managed_by          = "terraform"
    owner               = var.owner
    cost_center         = var.cost_center
    data_classification = var.data_classification
  }

  # This file is consumed by both Terraform and the release workflow. It is
  # the single source of truth for repository names and listening ports.
  service_contract = jsondecode(file("${path.module}/service-contract.json"))
}
