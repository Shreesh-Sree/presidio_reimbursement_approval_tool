# --- Workload identities: backend data access is isolated from advisory apps ---

resource "azurerm_user_assigned_identity" "backend" {
  name                = "${var.name_prefix}-api-id"
  resource_group_name = var.resource_group_name
  location            = var.location

  tags = var.tags
}

resource "azurerm_user_assigned_identity" "advisory" {
  name                = "${var.name_prefix}-advisory-id"
  resource_group_name = var.resource_group_name
  location            = var.location

  tags = var.tags
}

# Both workload identities can pull only from this registry and read Key Vault
# secrets referenced by their Container App revisions. Blob data access is
# deliberately granted to the backend identity only.
resource "azurerm_role_assignment" "acr_pull" {
  for_each = {
    backend  = azurerm_user_assigned_identity.backend.principal_id
    advisory = azurerm_user_assigned_identity.advisory.principal_id
  }

  scope                = var.acr_id
  role_definition_name = "AcrPull"
  principal_id         = each.value
}

resource "azurerm_role_assignment" "kv_secrets_user" {
  for_each = {
    backend  = azurerm_user_assigned_identity.backend.principal_id
    advisory = azurerm_user_assigned_identity.advisory.principal_id
  }

  scope                = var.key_vault_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = each.value
}

resource "azurerm_role_assignment" "backend_blob_data_contributor" {
  scope                = var.storage_container_resource_manager_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.backend.principal_id
}

# --- Container Apps Environment ---

resource "azurerm_container_app_environment" "main" {
  name                           = "${var.name_prefix}-env"
  resource_group_name            = var.resource_group_name
  location                       = var.location
  log_analytics_workspace_id     = var.log_analytics_workspace_id
  infrastructure_subnet_id       = var.infrastructure_subnet_id
  internal_load_balancer_enabled = false

  tags = var.tags
}

# --- Container App: backend (external ingress) ---

resource "azurerm_container_app" "backend" {
  name                         = "${var.name_prefix}-api"
  resource_group_name          = var.resource_group_name
  container_app_environment_id = azurerm_container_app_environment.main.id
  revision_mode                = "Single"

  tags = var.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.backend.id]
  }

  registry {
    server   = var.acr_login_server
    identity = azurerm_user_assigned_identity.backend.id
  }

  secret {
    name                = "database-url"
    key_vault_secret_id = var.database_url_secret_uri
    identity            = azurerm_user_assigned_identity.backend.id
  }

  secret {
    name                = "jwt-secret"
    key_vault_secret_id = var.jwt_secret_secret_uri
    identity            = azurerm_user_assigned_identity.backend.id
  }

  secret {
    name                = "supabase-jwt-secret"
    key_vault_secret_id = var.supabase_jwt_secret_secret_uri
    identity            = azurerm_user_assigned_identity.backend.id
  }

  secret {
    name                = "supabase-service-role-key"
    key_vault_secret_id = var.supabase_service_role_key_secret_uri
    identity            = azurerm_user_assigned_identity.backend.id
  }

  secret {
    name                = "super-admin-email"
    key_vault_secret_id = var.super_admin_email_secret_uri
    identity            = azurerm_user_assigned_identity.backend.id
  }

  secret {
    name                = "azure-communication-connection-string"
    key_vault_secret_id = var.azure_communication_connection_string_secret_uri
    identity            = azurerm_user_assigned_identity.backend.id
  }

  secret {
    name                = "ai-review-service-token"
    key_vault_secret_id = var.ai_review_service_token_secret_uri
    identity            = azurerm_user_assigned_identity.backend.id
  }

  secret {
    name                = "ai-review-reference-hmac-key"
    key_vault_secret_id = var.ai_review_reference_hmac_key_secret_uri
    identity            = azurerm_user_assigned_identity.backend.id
  }

  secret {
    name                = "receipt-intelligence-service-token"
    key_vault_secret_id = var.receipt_intelligence_token_secret_uri
    identity            = azurerm_user_assigned_identity.backend.id
  }

  secret {
    name                = "policy-assistant-service-token"
    key_vault_secret_id = var.policy_assistant_token_secret_uri
    identity            = azurerm_user_assigned_identity.backend.id
  }

  secret {
    name                = "policy-assistant-reference-hmac-key"
    key_vault_secret_id = var.policy_assistant_hmac_key_secret_uri
    identity            = azurerm_user_assigned_identity.backend.id
  }

  template {
    # Keep the interactive API warm: it authenticates the browser before the
    # dashboard can render, so a scale-from-zero cold start is user-visible.
    min_replicas = 1
    max_replicas = 1

    container {
      name   = "backend"
      image  = "${var.acr_login_server}/${var.service_contract.backend.repository}@${var.backend_image_digest}"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
      }

      env {
        name        = "JWT_SECRET"
        secret_name = "jwt-secret"
      }

      env {
        name  = "AUTH_PROVIDER"
        value = "supabase"
      }

      env {
        name  = "DEPLOYMENT_ENVIRONMENT"
        value = "production"
      }

      env {
        name  = "SUPABASE_URL"
        value = var.supabase_url
      }

      env {
        name        = "SUPABASE_JWT_SECRET"
        secret_name = "supabase-jwt-secret"
      }

      env {
        name        = "SUPABASE_SERVICE_ROLE_KEY"
        secret_name = "supabase-service-role-key"
      }

      env {
        name        = "SUPER_ADMIN_EMAIL"
        secret_name = "super-admin-email"
      }

      env {
        name  = "EMAIL_DELIVERY_ENABLED"
        value = tostring(var.email_delivery_enabled)
      }

      env {
        name        = "AZURE_COMMUNICATION_CONNECTION_STRING"
        secret_name = "azure-communication-connection-string"
      }

      env {
        name  = "AZURE_COMMUNICATION_SENDER"
        value = var.azure_communication_sender
      }

      env {
        name  = "CORS_ORIGINS"
        value = var.cors_origins
      }

      env {
        name  = "STORAGE_BACKEND"
        value = "azure"
      }

      env {
        name  = "AZURE_STORAGE_ACCOUNT_URL"
        value = var.storage_account_url
      }

      env {
        name  = "AZURE_STORAGE_CONTAINER"
        value = var.storage_container_name
      }

      env {
        name  = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.backend.client_id
      }

      env {
        name  = "AI_REVIEW_SERVICE_URL"
        value = "https://${azurerm_container_app.ai_review.ingress[0].fqdn}"
      }

      env {
        name        = "AI_REVIEW_SERVICE_TOKEN"
        secret_name = "ai-review-service-token"
      }

      env {
        name        = "AI_REVIEW_REFERENCE_HMAC_KEY"
        secret_name = "ai-review-reference-hmac-key"
      }

      env {
        name  = "RECEIPT_INTELLIGENCE_SERVICE_URL"
        value = "https://${azurerm_container_app.receipt_intelligence.ingress[0].fqdn}"
      }

      env {
        name        = "RECEIPT_INTELLIGENCE_SERVICE_TOKEN"
        secret_name = "receipt-intelligence-service-token"
      }

      env {
        name  = "POLICY_ASSISTANT_SERVICE_URL"
        value = "https://${azurerm_container_app.policy_assistant.ingress[0].fqdn}"
      }

      env {
        name        = "POLICY_ASSISTANT_SERVICE_TOKEN"
        secret_name = "policy-assistant-service-token"
      }

      env {
        name        = "POLICY_ASSISTANT_REFERENCE_HMAC_KEY"
        secret_name = "policy-assistant-reference-hmac-key"
      }

      liveness_probe {
        transport = "HTTP"
        path      = "/api/health"
        port      = var.service_contract.backend.port
      }

      readiness_probe {
        transport = "HTTP"
        path      = "/api/ready"
        port      = var.service_contract.backend.port
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = var.service_contract.backend.port
    transport        = "http"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  depends_on = [
    azurerm_role_assignment.acr_pull,
    azurerm_role_assignment.kv_secrets_user,
    azurerm_role_assignment.backend_blob_data_contributor,
    azurerm_container_app.ai_review,
    azurerm_container_app.receipt_intelligence,
    azurerm_container_app.policy_assistant,
  ]
}

# Durable work is never coupled to a browser request or an API process-local
# background task. This scheduled job invokes the lease-based worker once every
# five minutes using the same immutable backend image and Key Vault references.
resource "azurerm_container_app_job" "durable_worker" {
  name                         = "${var.name_prefix}-worker"
  resource_group_name          = var.resource_group_name
  location                     = var.location
  container_app_environment_id = azurerm_container_app_environment.main.id
  replica_timeout_in_seconds   = 300
  replica_retry_limit          = 2

  tags = var.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.backend.id]
  }

  registry {
    server   = var.acr_login_server
    identity = azurerm_user_assigned_identity.backend.id
  }

  secret {
    name                = "database-url"
    key_vault_secret_id = var.database_url_secret_uri
    identity            = azurerm_user_assigned_identity.backend.id
  }

  secret {
    name                = "jwt-secret"
    key_vault_secret_id = var.jwt_secret_secret_uri
    identity            = azurerm_user_assigned_identity.backend.id
  }

  secret {
    name                = "azure-communication-connection-string"
    key_vault_secret_id = var.azure_communication_connection_string_secret_uri
    identity            = azurerm_user_assigned_identity.backend.id
  }

  secret {
    name                = "ai-review-service-token"
    key_vault_secret_id = var.ai_review_service_token_secret_uri
    identity            = azurerm_user_assigned_identity.backend.id
  }

  secret {
    name                = "ai-review-reference-hmac-key"
    key_vault_secret_id = var.ai_review_reference_hmac_key_secret_uri
    identity            = azurerm_user_assigned_identity.backend.id
  }

  schedule_trigger_config {
    cron_expression          = "*/5 * * * *"
    parallelism              = 1
    replica_completion_count = 1
  }

  template {
    container {
      name    = "durable-worker"
      image   = "${var.acr_login_server}/${var.service_contract.backend.repository}@${var.backend_image_digest}"
      cpu     = 0.25
      memory  = "0.5Gi"
      command = ["python", "-m", "app.worker"]
      args    = ["--once"]

      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
      }

      env {
        name        = "JWT_SECRET"
        secret_name = "jwt-secret"
      }

      env {
        name  = "AUTH_PROVIDER"
        value = "supabase"
      }

      env {
        name  = "DEPLOYMENT_ENVIRONMENT"
        value = "production"
      }

      env {
        name  = "STORAGE_BACKEND"
        value = "azure"
      }

      env {
        name  = "AZURE_STORAGE_ACCOUNT_URL"
        value = var.storage_account_url
      }

      env {
        name  = "AZURE_STORAGE_CONTAINER"
        value = var.storage_container_name
      }

      env {
        name  = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.backend.client_id
      }

      env {
        name  = "EMAIL_DELIVERY_ENABLED"
        value = tostring(var.email_delivery_enabled)
      }

      env {
        name        = "AZURE_COMMUNICATION_CONNECTION_STRING"
        secret_name = "azure-communication-connection-string"
      }

      env {
        name  = "AZURE_COMMUNICATION_SENDER"
        value = var.azure_communication_sender
      }

      env {
        name  = "AI_REVIEW_SERVICE_URL"
        value = "https://${azurerm_container_app.ai_review.ingress[0].fqdn}"
      }

      env {
        name        = "AI_REVIEW_SERVICE_TOKEN"
        secret_name = "ai-review-service-token"
      }

      env {
        name        = "AI_REVIEW_REFERENCE_HMAC_KEY"
        secret_name = "ai-review-reference-hmac-key"
      }
    }
  }

  depends_on = [
    azurerm_role_assignment.acr_pull,
    azurerm_role_assignment.kv_secrets_user,
    azurerm_container_app.ai_review,
  ]
}

# --- Container App: ai_review_service (internal) ---

resource "azurerm_container_app" "ai_review" {
  name                         = "${var.name_prefix}-ai"
  resource_group_name          = var.resource_group_name
  container_app_environment_id = azurerm_container_app_environment.main.id
  revision_mode                = "Single"

  tags = var.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.advisory.id]
  }

  registry {
    server   = var.acr_login_server
    identity = azurerm_user_assigned_identity.advisory.id
  }

  secret {
    name                = "ai-review-service-token"
    key_vault_secret_id = var.ai_review_service_token_secret_uri
    identity            = azurerm_user_assigned_identity.advisory.id
  }

  secret {
    name                = "ai-review-reference-hmac-key"
    key_vault_secret_id = var.ai_review_reference_hmac_key_secret_uri
    identity            = azurerm_user_assigned_identity.advisory.id
  }

  secret {
    name                = "ai-review-database-url"
    key_vault_secret_id = var.ai_review_database_url_secret_uri
    identity            = azurerm_user_assigned_identity.advisory.id
  }

  template {
    min_replicas = 1
    max_replicas = 1

    container {
      name   = "ai-review"
      image  = "${var.acr_login_server}/${var.service_contract.ai_review.repository}@${var.ai_review_image_digest}"
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name        = "AI_REVIEW_SERVICE_TOKEN"
        secret_name = "ai-review-service-token"
      }

      env {
        name        = "AI_REVIEW_REFERENCE_HMAC_KEY"
        secret_name = "ai-review-reference-hmac-key"
      }

      env {
        name  = "AI_REVIEW_ENVIRONMENT"
        value = "production"
      }

      env {
        name  = "AI_REVIEW_PERSISTENCE_BACKEND"
        value = "postgresql"
      }

      env {
        name        = "AI_REVIEW_DATABASE_URL"
        secret_name = "ai-review-database-url"
      }

      liveness_probe {
        transport = "HTTP"
        path      = "/health"
        port      = var.service_contract.ai_review.port
      }

      readiness_probe {
        transport = "HTTP"
        path      = "/ready"
        port      = var.service_contract.ai_review.port
      }
    }
  }

  ingress {
    external_enabled = false
    target_port      = var.service_contract.ai_review.port
    transport        = "http"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  depends_on = [
    azurerm_role_assignment.acr_pull,
    azurerm_role_assignment.kv_secrets_user,
  ]
}

# --- Container App: receipt_intelligence_service (internal) ---

resource "azurerm_container_app" "receipt_intelligence" {
  name                         = "${var.name_prefix}-rcpt"
  resource_group_name          = var.resource_group_name
  container_app_environment_id = azurerm_container_app_environment.main.id
  revision_mode                = "Single"

  tags = var.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.advisory.id]
  }

  registry {
    server   = var.acr_login_server
    identity = azurerm_user_assigned_identity.advisory.id
  }

  secret {
    name                = "receipt-intelligence-service-token"
    key_vault_secret_id = var.receipt_intelligence_token_secret_uri
    identity            = azurerm_user_assigned_identity.advisory.id
  }

  secret {
    name                = "receipt-intelligence-database-url"
    key_vault_secret_id = var.receipt_intelligence_database_url_secret_uri
    identity            = azurerm_user_assigned_identity.advisory.id
  }

  template {
    min_replicas = 1
    max_replicas = 1

    container {
      name   = "receipt-intelligence"
      image  = "${var.acr_login_server}/${var.service_contract.receipt_intelligence.repository}@${var.receipt_intelligence_image_digest}"
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name        = "RECEIPT_INTELLIGENCE_SERVICE_TOKEN"
        secret_name = "receipt-intelligence-service-token"
      }

      env {
        name  = "RECEIPT_INTELLIGENCE_ENVIRONMENT"
        value = "production"
      }

      env {
        name  = "RECEIPT_INTELLIGENCE_PERSISTENCE_BACKEND"
        value = "postgresql"
      }

      env {
        name        = "RECEIPT_INTELLIGENCE_DATABASE_URL"
        secret_name = "receipt-intelligence-database-url"
      }

      liveness_probe {
        transport = "HTTP"
        path      = "/health"
        port      = var.service_contract.receipt_intelligence.port
      }

      readiness_probe {
        transport = "HTTP"
        path      = "/ready"
        port      = var.service_contract.receipt_intelligence.port
      }
    }
  }

  ingress {
    external_enabled = false
    target_port      = var.service_contract.receipt_intelligence.port
    transport        = "http"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  depends_on = [
    azurerm_role_assignment.acr_pull,
    azurerm_role_assignment.kv_secrets_user,
  ]
}

# --- Container App: policy_assistant_service (internal) ---

resource "azurerm_container_app" "policy_assistant" {
  name                         = "${var.name_prefix}-pol"
  resource_group_name          = var.resource_group_name
  container_app_environment_id = azurerm_container_app_environment.main.id
  revision_mode                = "Single"

  tags = var.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.advisory.id]
  }

  registry {
    server   = var.acr_login_server
    identity = azurerm_user_assigned_identity.advisory.id
  }

  secret {
    name                = "policy-assistant-service-token"
    key_vault_secret_id = var.policy_assistant_token_secret_uri
    identity            = azurerm_user_assigned_identity.advisory.id
  }

  secret {
    name                = "policy-assistant-reference-hmac-key"
    key_vault_secret_id = var.policy_assistant_hmac_key_secret_uri
    identity            = azurerm_user_assigned_identity.advisory.id
  }

  secret {
    name                = "policy-assistant-database-url"
    key_vault_secret_id = var.policy_assistant_database_url_secret_uri
    identity            = azurerm_user_assigned_identity.advisory.id
  }

  template {
    min_replicas = 1
    max_replicas = 1

    container {
      name   = "policy-assistant"
      image  = "${var.acr_login_server}/${var.service_contract.policy_assistant.repository}@${var.policy_assistant_image_digest}"
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name        = "POLICY_ASSISTANT_SERVICE_TOKEN"
        secret_name = "policy-assistant-service-token"
      }

      env {
        name        = "POLICY_ASSISTANT_REFERENCE_HMAC_KEY"
        secret_name = "policy-assistant-reference-hmac-key"
      }

      env {
        name  = "POLICY_ASSISTANT_ENVIRONMENT"
        value = "production"
      }

      env {
        name  = "POLICY_ASSISTANT_PERSISTENCE_BACKEND"
        value = "postgresql"
      }

      env {
        name        = "POLICY_ASSISTANT_DATABASE_URL"
        secret_name = "policy-assistant-database-url"
      }

      liveness_probe {
        transport = "HTTP"
        path      = "/health"
        port      = var.service_contract.policy_assistant.port
      }

      readiness_probe {
        transport = "HTTP"
        path      = "/ready"
        port      = var.service_contract.policy_assistant.port
      }
    }
  }

  ingress {
    external_enabled = false
    target_port      = var.service_contract.policy_assistant.port
    transport        = "http"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  depends_on = [
    azurerm_role_assignment.acr_pull,
    azurerm_role_assignment.kv_secrets_user,
  ]
}
