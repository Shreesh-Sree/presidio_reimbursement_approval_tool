locals {
  application_runtime_environment = {
    DATABASE_URL                         = "postgresql+psycopg://${var.database_username}:${var.database_password}@${var.database_host}:${var.database_port}/${var.database_name}?sslmode=require"
    JWT_SECRET                           = var.jwt_secret
    JWT_ALGORITHM                        = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES          = "1440"
    AWS_REGION                           = var.aws_region
    STORAGE_BACKEND                      = "s3"
    S3_BUCKET                            = var.uploads_bucket_name
    CORS_ORIGINS                         = "https://${var.app_domain}"
    MAX_POLICY_DOCUMENT_BYTES            = "15728640"
    MAX_RECEIPT_BYTES                    = "10485760"
    AI_REVIEW_SERVICE_URL                = "http://ai-review:8011"
    AI_REVIEW_SERVICE_TOKEN              = var.ai_service_token
    AI_REVIEW_TIMEOUT_SECONDS            = "5"
    AI_REVIEW_PROCESS_INLINE             = "false"
    AI_REVIEW_REFERENCE_HMAC_KEY         = var.ai_review_reference_hmac_key
    RECEIPT_INTELLIGENCE_SERVICE_URL     = "http://receipt-intelligence:8012"
    RECEIPT_INTELLIGENCE_SERVICE_TOKEN   = var.receipt_intelligence_service_token
    RECEIPT_INTELLIGENCE_TIMEOUT_SECONDS = "4"
    POLICY_ASSISTANT_SERVICE_URL         = "http://policy-assistant:8013"
    POLICY_ASSISTANT_SERVICE_TOKEN       = var.policy_assistant_service_token
    POLICY_ASSISTANT_TIMEOUT_SECONDS     = "4"
    POLICY_ASSISTANT_REFERENCE_HMAC_KEY  = var.policy_assistant_reference_hmac_key
    EMAIL_DELIVERY_ENABLED               = tostring(var.email_delivery_enabled)
    SMTP_HOST                            = var.smtp_host
    SMTP_PORT                            = "587"
    SMTP_USER                            = var.smtp_username
    SMTP_PASSWORD                        = var.smtp_password
    SMTP_FROM                            = var.smtp_from
    SMTP_USE_TLS                         = "true"
    SMTP_TIMEOUT_SECONDS                 = "10"
  }

  ai_review_runtime_environment = {
    AI_REVIEW_DATABASE_PATH                    = "/data/ai-review.sqlite3"
    AI_REVIEW_SERVICE_TOKEN                    = var.ai_service_token
    AI_REVIEW_AUTO_PROCESS_JOBS                = "true"
    AI_REVIEW_LOCAL_WORKER_MAX_CONCURRENCY     = "1"
    AI_REVIEW_LOCAL_WORKER_RETRY_DELAY_SECONDS = "0.25"
    AI_REVIEW_JOB_MAX_ATTEMPTS                 = "3"
    AI_REVIEW_GEMINI_API_KEY                   = var.gemini_api_key
    AI_REVIEW_GEMINI_MODEL                     = "gemini-2.5-flash"
  }

  receipt_intelligence_runtime_environment = {
    RECEIPT_INTELLIGENCE_DATABASE_PATH  = "/data/receipt-intelligence.sqlite3"
    RECEIPT_INTELLIGENCE_SERVICE_TOKEN  = var.receipt_intelligence_service_token
    RECEIPT_INTELLIGENCE_MAX_FILE_BYTES = "10485760"
    RECEIPT_INTELLIGENCE_MAX_TEXT_CHARS = "24000"
  }

  policy_assistant_runtime_environment = {
    POLICY_ASSISTANT_DATABASE_PATH            = "/data/policy-assistant.sqlite3"
    POLICY_ASSISTANT_SERVICE_TOKEN            = var.policy_assistant_service_token
    POLICY_ASSISTANT_PROVIDER_MODE            = "deterministic"
    POLICY_ASSISTANT_ENABLE_EXTERNAL_PROVIDER = "false"
  }
}

resource "aws_secretsmanager_secret_version" "application" {
  secret_id     = var.application_secret_arn
  secret_string = jsonencode(local.application_runtime_environment)

  lifecycle {
    precondition {
      condition = !var.email_delivery_enabled || (
        trimspace(coalesce(var.smtp_username, "")) != "" &&
        trimspace(coalesce(var.smtp_password, "")) != ""
      )
      error_message = "SES SMTP credentials are required when email delivery is enabled."
    }
  }
}

resource "aws_secretsmanager_secret_version" "ai_review" {
  secret_id     = var.ai_review_secret_arn
  secret_string = jsonencode(local.ai_review_runtime_environment)
}

resource "aws_secretsmanager_secret_version" "receipt_intelligence" {
  secret_id     = var.receipt_intelligence_secret_arn
  secret_string = jsonencode(local.receipt_intelligence_runtime_environment)
}

resource "aws_secretsmanager_secret_version" "policy_assistant" {
  secret_id     = var.policy_assistant_secret_arn
  secret_string = jsonencode(local.policy_assistant_runtime_environment)
}
