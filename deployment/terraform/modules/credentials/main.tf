resource "random_password" "database" {
  length  = 40
  special = false
}

resource "random_password" "jwt" {
  length  = 64
  special = false
}

resource "random_password" "ai_service" {
  length  = 48
  special = false
}

resource "aws_secretsmanager_secret" "application" {
  name                    = "${var.name_prefix}/application-runtime"
  description             = "Runtime configuration for the reimbursement API and isolated AI reviewer"
  recovery_window_in_days = 7

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-application-runtime"
  })
}

# The AI process receives a distinct, minimal secret. It must not be able to
# obtain the reimbursement database URL, JWT signing secret, SMTP credentials,
# or upload-bucket configuration.
resource "aws_secretsmanager_secret" "ai_review" {
  name                    = "${var.name_prefix}/ai-review-runtime"
  description             = "Minimal runtime configuration for the isolated advisory AI reviewer"
  recovery_window_in_days = 7

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-ai-review-runtime"
  })
}
