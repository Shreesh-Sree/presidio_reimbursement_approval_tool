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

# This key is held by the core API only. It stabilizes the AI review service's
# opaque report/event references across bearer-token rotations and must never
# be supplied to the AI-review container itself.
resource "random_password" "ai_review_reference_hmac" {
  length  = 64
  special = false
}

resource "random_password" "receipt_intelligence_service" {
  length  = 48
  special = false
}

resource "random_password" "policy_assistant_service" {
  length  = 48
  special = false
}

# This key is held by the core API only. It stabilizes the policy assistant's
# opaque tenant/policy references across bearer-token rotations and must never
# be supplied to the assistant container itself.
resource "random_password" "policy_assistant_reference_hmac" {
  length  = 64
  special = false
}

resource "aws_secretsmanager_secret" "application" {
  name                    = "${var.name_prefix}/application-runtime"
  description             = "Runtime configuration for the reimbursement API and its isolated advisory services"
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

# Each optional AI service has a separate runtime secret. These secrets are
# deliberately limited to a service token and a local SQLite path; they never
# contain the core PostgreSQL URL, JWT signing key, S3 details, or SMTP values.
resource "aws_secretsmanager_secret" "receipt_intelligence" {
  name                    = "${var.name_prefix}/receipt-intelligence-runtime"
  description             = "Minimal runtime configuration for isolated receipt intelligence"
  recovery_window_in_days = 7

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-receipt-intelligence-runtime"
  })
}

resource "aws_secretsmanager_secret" "policy_assistant" {
  name                    = "${var.name_prefix}/policy-assistant-runtime"
  description             = "Minimal runtime configuration for isolated policy assistant"
  recovery_window_in_days = 7

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-policy-assistant-runtime"
  })
}
