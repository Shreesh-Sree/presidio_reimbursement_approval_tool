# --- User-Assigned Managed Identity for ACR pull and Key Vault access ---

resource "azurerm_user_assigned_identity" "container_apps" {
  name                = "${var.name_prefix}-id"
  resource_group_name = var.resource_group_name
  location            = var.location

  tags = var.tags
}

# Grant ACR pull to the managed identity
resource "azurerm_role_assignment" "acr_pull" {
  scope                = var.acr_id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.container_apps.principal_id
}

# Grant Key Vault Secrets User to the managed identity
resource "azurerm_role_assignment" "kv_secrets_user" {
  scope                = var.key_vault_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.container_apps.principal_id
}

# --- Container Apps Environment ---

resource "azurerm_container_app_environment" "main" {
  name                       = "${var.name_prefix}-env"
  resource_group_name        = var.resource_group_name
  location                   = var.location
  log_analytics_workspace_id = var.log_analytics_workspace_id

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
    identity_ids = [azurerm_user_assigned_identity.container_apps.id]
  }

  registry {
    server   = var.acr_login_server
    identity = azurerm_user_assigned_identity.container_apps.id
  }

  secret {
    name                = "database-url"
    key_vault_secret_id = var.database_url_secret_uri
    identity            = azurerm_user_assigned_identity.container_apps.id
  }

  secret {
    name                = "jwt-secret"
    key_vault_secret_id = var.jwt_secret_secret_uri
    identity            = azurerm_user_assigned_identity.container_apps.id
  }

  secret {
    name                = "supabase-jwt-secret"
    key_vault_secret_id = var.supabase_jwt_secret_secret_uri
    identity            = azurerm_user_assigned_identity.container_apps.id
  }

  secret {
    name                = "supabase-service-role-key"
    key_vault_secret_id = var.supabase_service_role_key_secret_uri
    identity            = azurerm_user_assigned_identity.container_apps.id
  }

  secret {
    name                = "super-admin-email"
    key_vault_secret_id = var.super_admin_email_secret_uri
    identity            = azurerm_user_assigned_identity.container_apps.id
  }

  secret {
    name                = "ai-review-service-token"
    key_vault_secret_id = var.ai_review_service_token_secret_uri
    identity            = azurerm_user_assigned_identity.container_apps.id
  }

  secret {
    name                = "ai-review-reference-hmac-key"
    key_vault_secret_id = var.ai_review_reference_hmac_key_secret_uri
    identity            = azurerm_user_assigned_identity.container_apps.id
  }

  secret {
    name                = "receipt-intelligence-service-token"
    key_vault_secret_id = var.receipt_intelligence_token_secret_uri
    identity            = azurerm_user_assigned_identity.container_apps.id
  }

  secret {
    name                = "policy-assistant-service-token"
    key_vault_secret_id = var.policy_assistant_token_secret_uri
    identity            = azurerm_user_assigned_identity.container_apps.id
  }

  secret {
    name                = "policy-assistant-reference-hmac-key"
    key_vault_secret_id = var.policy_assistant_hmac_key_secret_uri
    identity            = azurerm_user_assigned_identity.container_apps.id
  }

  template {
    # Keep the interactive API warm: it authenticates the browser before the
    # dashboard can render, so a scale-from-zero cold start is user-visible.
    min_replicas = 1
    max_replicas = 1

    container {
      name   = "backend"
      image  = "${var.acr_login_server}/backend:${var.backend_image_tag}"
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
        name  = "CORS_ORIGINS"
        value = var.cors_origins
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
        port      = 8000
      }

      readiness_probe {
        transport = "HTTP"
        path      = "/api/health"
        port      = 8000
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "http"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  depends_on = [
    azurerm_role_assignment.acr_pull,
    azurerm_role_assignment.kv_secrets_user,
    azurerm_container_app.ai_review,
    azurerm_container_app.receipt_intelligence,
    azurerm_container_app.policy_assistant,
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
    identity_ids = [azurerm_user_assigned_identity.container_apps.id]
  }

  registry {
    server   = var.acr_login_server
    identity = azurerm_user_assigned_identity.container_apps.id
  }

  secret {
    name                = "ai-review-service-token"
    key_vault_secret_id = var.ai_review_service_token_secret_uri
    identity            = azurerm_user_assigned_identity.container_apps.id
  }

  secret {
    name                = "ai-review-reference-hmac-key"
    key_vault_secret_id = var.ai_review_reference_hmac_key_secret_uri
    identity            = azurerm_user_assigned_identity.container_apps.id
  }

  template {
    min_replicas = 0
    max_replicas = 1

    container {
      name   = "ai-review"
      image  = "${var.acr_login_server}/ai-review-service:${var.ai_review_image_tag}"
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name        = "SERVICE_TOKEN"
        secret_name = "ai-review-service-token"
      }

      env {
        name        = "REFERENCE_HMAC_KEY"
        secret_name = "ai-review-reference-hmac-key"
      }

      liveness_probe {
        transport = "HTTP"
        path      = "/health"
        port      = 8000
      }

      readiness_probe {
        transport = "HTTP"
        path      = "/health"
        port      = 8000
      }
    }
  }

  ingress {
    external_enabled = false
    target_port      = 8000
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
    identity_ids = [azurerm_user_assigned_identity.container_apps.id]
  }

  registry {
    server   = var.acr_login_server
    identity = azurerm_user_assigned_identity.container_apps.id
  }

  secret {
    name                = "receipt-intelligence-service-token"
    key_vault_secret_id = var.receipt_intelligence_token_secret_uri
    identity            = azurerm_user_assigned_identity.container_apps.id
  }

  template {
    min_replicas = 0
    max_replicas = 1

    container {
      name   = "receipt-intelligence"
      image  = "${var.acr_login_server}/receipt-intelligence-service:${var.receipt_intelligence_image_tag}"
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name        = "SERVICE_TOKEN"
        secret_name = "receipt-intelligence-service-token"
      }

      liveness_probe {
        transport = "HTTP"
        path      = "/health"
        port      = 8000
      }

      readiness_probe {
        transport = "HTTP"
        path      = "/health"
        port      = 8000
      }
    }
  }

  ingress {
    external_enabled = false
    target_port      = 8000
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
    identity_ids = [azurerm_user_assigned_identity.container_apps.id]
  }

  registry {
    server   = var.acr_login_server
    identity = azurerm_user_assigned_identity.container_apps.id
  }

  secret {
    name                = "policy-assistant-service-token"
    key_vault_secret_id = var.policy_assistant_token_secret_uri
    identity            = azurerm_user_assigned_identity.container_apps.id
  }

  secret {
    name                = "policy-assistant-reference-hmac-key"
    key_vault_secret_id = var.policy_assistant_hmac_key_secret_uri
    identity            = azurerm_user_assigned_identity.container_apps.id
  }

  template {
    min_replicas = 0
    max_replicas = 1

    container {
      name   = "policy-assistant"
      image  = "${var.acr_login_server}/policy-assistant-service:${var.policy_assistant_image_tag}"
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name        = "SERVICE_TOKEN"
        secret_name = "policy-assistant-service-token"
      }

      env {
        name        = "REFERENCE_HMAC_KEY"
        secret_name = "policy-assistant-reference-hmac-key"
      }

      liveness_probe {
        transport = "HTTP"
        path      = "/health"
        port      = 8000
      }

      readiness_probe {
        transport = "HTTP"
        path      = "/health"
        port      = 8000
      }
    }
  }

  ingress {
    external_enabled = false
    target_port      = 8000
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
