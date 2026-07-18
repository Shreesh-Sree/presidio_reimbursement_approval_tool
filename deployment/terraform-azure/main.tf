data "azurerm_resource_group" "main" {
  name = var.resource_group_name
}

data "azurerm_client_config" "current" {}

module "logging" {
  source = "./modules/logging"

  name_prefix         = local.name_prefix
  resource_group_name = data.azurerm_resource_group.main.name
  location            = var.location
  retention_days      = var.log_retention_days
  tags                = local.common_tags
}

module "registry" {
  source = "./modules/registry"

  name_prefix         = local.name_prefix
  resource_group_name = data.azurerm_resource_group.main.name
  location            = var.location
  tags                = local.common_tags
}

module "keyvault" {
  source = "./modules/keyvault"

  name_prefix         = local.name_prefix
  resource_group_name = data.azurerm_resource_group.main.name
  location            = var.location
  tenant_id           = data.azurerm_client_config.current.tenant_id
  deployer_object_id  = data.azurerm_client_config.current.object_id
  tags                = local.common_tags

  secrets = {
    "database-url"                       = var.database_url
    "jwt-secret"                         = var.jwt_secret
    "supabase-jwt-secret"                = var.supabase_jwt_secret
    "supabase-service-role-key"          = var.supabase_service_role_key
    "super-admin-email"                  = var.super_admin_email
    "ai-review-service-token"            = var.ai_review_service_token
    "ai-review-reference-hmac-key"       = var.ai_review_reference_hmac_key
    "receipt-intelligence-service-token"  = var.receipt_intelligence_service_token
    "policy-assistant-service-token"      = var.policy_assistant_service_token
    "policy-assistant-reference-hmac-key" = var.policy_assistant_reference_hmac_key
  }
}

module "storage" {
  source = "./modules/storage"

  name_prefix         = local.name_prefix
  resource_group_name = data.azurerm_resource_group.main.name
  location            = var.location
  tags                = local.common_tags
}

module "container_apps" {
  source = "./modules/container_apps"

  name_prefix         = local.name_prefix
  resource_group_name = data.azurerm_resource_group.main.name
  location            = var.location
  tags                = local.common_tags

  log_analytics_workspace_id          = module.logging.workspace_id
  log_analytics_workspace_primary_key = module.logging.primary_shared_key

  acr_login_server = module.registry.login_server
  acr_id           = module.registry.id

  key_vault_id  = module.keyvault.id
  key_vault_uri = module.keyvault.vault_uri

  backend_image_tag                = var.backend_image_tag
  ai_review_image_tag              = var.ai_review_image_tag
  receipt_intelligence_image_tag   = var.receipt_intelligence_image_tag
  policy_assistant_image_tag       = var.policy_assistant_image_tag

  # Env var values (non-secret)
  supabase_url = var.supabase_url
  cors_origins = var.cors_origins

  # Secret references (Key Vault secret URIs)
  database_url_secret_uri                   = module.keyvault.secret_uris["database-url"]
  jwt_secret_secret_uri                     = module.keyvault.secret_uris["jwt-secret"]
  supabase_jwt_secret_secret_uri            = module.keyvault.secret_uris["supabase-jwt-secret"]
  supabase_service_role_key_secret_uri      = module.keyvault.secret_uris["supabase-service-role-key"]
  super_admin_email_secret_uri              = module.keyvault.secret_uris["super-admin-email"]
  ai_review_service_token_secret_uri        = module.keyvault.secret_uris["ai-review-service-token"]
  ai_review_reference_hmac_key_secret_uri   = module.keyvault.secret_uris["ai-review-reference-hmac-key"]
  receipt_intelligence_token_secret_uri     = module.keyvault.secret_uris["receipt-intelligence-service-token"]
  policy_assistant_token_secret_uri         = module.keyvault.secret_uris["policy-assistant-service-token"]
  policy_assistant_hmac_key_secret_uri      = module.keyvault.secret_uris["policy-assistant-reference-hmac-key"]

  depends_on = [module.logging, module.registry, module.keyvault]
}
