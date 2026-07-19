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
  alert_email         = var.alert_email
  tags                = local.common_tags
}

module "network" {
  source = "./modules/network"

  name_prefix                             = local.name_prefix
  resource_group_name                     = data.azurerm_resource_group.main.name
  location                                = var.location
  address_space                           = var.network_address_space
  container_apps_subnet_address_prefix    = var.container_apps_subnet_address_prefix
  private_endpoints_subnet_address_prefix = var.private_endpoints_subnet_address_prefix
  tags                                    = local.common_tags
}

module "registry" {
  source = "./modules/registry"

  name_prefix                = local.name_prefix
  resource_group_name        = data.azurerm_resource_group.main.name
  location                   = var.location
  tags                       = local.common_tags
  private_endpoint_subnet_id = module.network.private_endpoint_subnet_id
  private_dns_zone_id        = module.network.private_dns_zone_ids["registry"]
}

module "keyvault" {
  source = "./modules/keyvault"

  name_prefix                     = local.name_prefix
  resource_group_name             = data.azurerm_resource_group.main.name
  location                        = var.location
  tenant_id                       = data.azurerm_client_config.current.tenant_id
  tags                            = local.common_tags
  container_apps_subnet_id        = module.network.container_apps_subnet_id
  private_endpoint_subnet_id      = module.network.private_endpoint_subnet_id
  private_dns_zone_id             = module.network.private_dns_zone_ids["key_vault"]
  secret_expiration_date          = var.key_vault_secret_expiration_date
  storage_cmk_key_expiration_date = var.storage_cmk_key_expiration_date

  secrets = {
    "database-url"                          = var.database_url
    "jwt-secret"                            = var.jwt_secret
    "supabase-jwt-secret"                   = var.supabase_jwt_secret
    "supabase-service-role-key"             = var.supabase_service_role_key
    "super-admin-email"                     = var.super_admin_email
    "azure-communication-connection-string" = var.azure_communication_connection_string
    "ai-review-service-token"               = var.ai_review_service_token
    "ai-review-database-url"                = var.ai_review_database_url
    "ai-review-reference-hmac-key"          = var.ai_review_reference_hmac_key
    "receipt-intelligence-service-token"    = var.receipt_intelligence_service_token
    "receipt-intelligence-database-url"     = var.receipt_intelligence_database_url
    "policy-assistant-service-token"        = var.policy_assistant_service_token
    "policy-assistant-database-url"         = var.policy_assistant_database_url
    "policy-assistant-reference-hmac-key"   = var.policy_assistant_reference_hmac_key
  }
}

module "storage" {
  source = "./modules/storage"

  name_prefix                = local.name_prefix
  resource_group_name        = data.azurerm_resource_group.main.name
  location                   = var.location
  tags                       = local.common_tags
  container_apps_subnet_id   = module.network.container_apps_subnet_id
  private_endpoint_subnet_id = module.network.private_endpoint_subnet_id
  private_dns_zone_id        = module.network.private_dns_zone_ids["blob"]
  key_vault_id               = module.keyvault.id
  customer_managed_key_id    = module.keyvault.storage_cmk_key_id
  log_analytics_workspace_id = module.logging.workspace_id
}

module "container_apps" {
  source = "./modules/container_apps"

  name_prefix         = local.name_prefix
  resource_group_name = data.azurerm_resource_group.main.name
  location            = var.location
  tags                = local.common_tags

  log_analytics_workspace_id = module.logging.workspace_id
  infrastructure_subnet_id   = module.network.container_apps_subnet_id

  acr_login_server = module.registry.login_server
  acr_id           = module.registry.id

  key_vault_id  = module.keyvault.id
  key_vault_uri = module.keyvault.vault_uri

  service_contract                  = local.service_contract
  backend_image_digest              = var.backend_image_digest
  ai_review_image_digest            = var.ai_review_image_digest
  receipt_intelligence_image_digest = var.receipt_intelligence_image_digest
  policy_assistant_image_digest     = var.policy_assistant_image_digest

  storage_account_url                   = module.storage.primary_blob_endpoint
  storage_container_name                = module.storage.container_name
  storage_container_resource_manager_id = module.storage.container_resource_manager_id

  # Env var values (non-secret)
  supabase_url               = var.supabase_url
  cors_origins               = var.cors_origins
  email_delivery_enabled     = var.email_delivery_enabled
  azure_communication_sender = var.azure_communication_sender

  # Secret references (Key Vault secret URIs)
  database_url_secret_uri                          = module.keyvault.secret_uris["database-url"]
  jwt_secret_secret_uri                            = module.keyvault.secret_uris["jwt-secret"]
  supabase_jwt_secret_secret_uri                   = module.keyvault.secret_uris["supabase-jwt-secret"]
  supabase_service_role_key_secret_uri             = module.keyvault.secret_uris["supabase-service-role-key"]
  super_admin_email_secret_uri                     = module.keyvault.secret_uris["super-admin-email"]
  azure_communication_connection_string_secret_uri = module.keyvault.secret_uris["azure-communication-connection-string"]
  ai_review_service_token_secret_uri               = module.keyvault.secret_uris["ai-review-service-token"]
  ai_review_database_url_secret_uri                = module.keyvault.secret_uris["ai-review-database-url"]
  ai_review_reference_hmac_key_secret_uri          = module.keyvault.secret_uris["ai-review-reference-hmac-key"]
  receipt_intelligence_token_secret_uri            = module.keyvault.secret_uris["receipt-intelligence-service-token"]
  receipt_intelligence_database_url_secret_uri     = module.keyvault.secret_uris["receipt-intelligence-database-url"]
  policy_assistant_token_secret_uri                = module.keyvault.secret_uris["policy-assistant-service-token"]
  policy_assistant_database_url_secret_uri         = module.keyvault.secret_uris["policy-assistant-database-url"]
  policy_assistant_hmac_key_secret_uri             = module.keyvault.secret_uris["policy-assistant-reference-hmac-key"]

  depends_on = [module.logging, module.registry, module.keyvault, module.storage]
}
