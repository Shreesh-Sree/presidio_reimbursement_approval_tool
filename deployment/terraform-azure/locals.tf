locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = {
    project     = var.project_name
    environment = var.environment
    managed_by  = "terraform"
  }

  # Container image names (without registry prefix)
  container_images = {
    backend                    = "backend"
    ai_review_service          = "ai-review-service"
    receipt_intelligence_service = "receipt-intelligence-service"
    policy_assistant_service    = "policy-assistant-service"
  }
}
