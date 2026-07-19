resource "azurerm_key_vault" "main" {
  # Key Vault names: 3-24 alphanumeric + hyphens, globally unique
  name                = "${substr(var.name_prefix, 0, 21)}kv"
  resource_group_name = var.resource_group_name
  location            = var.location
  tenant_id           = var.tenant_id
  sku_name            = "premium"

  rbac_authorization_enabled    = true
  purge_protection_enabled      = true
  soft_delete_retention_days    = 90
  public_network_access_enabled = false

  # Private Link is the data-plane boundary. The ACL remains deny-by-default
  # as defense in depth and documents the only workload subnet that may reach
  # the vault when a controlled bootstrap temporarily enables public access.
  network_acls {
    bypass                     = "None"
    default_action             = "Deny"
    ip_rules                   = []
    virtual_network_subnet_ids = [var.container_apps_subnet_id]
  }

  tags = var.tags
}

resource "azurerm_private_endpoint" "main" {
  name                = "${var.name_prefix}-kv-pe"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id

  private_service_connection {
    name                           = "${var.name_prefix}-kv-psc"
    private_connection_resource_id = azurerm_key_vault.main.id
    is_manual_connection           = false
    subresource_names              = ["vault"]
  }

  private_dns_zone_group {
    name                 = "default"
    private_dns_zone_ids = [var.private_dns_zone_id]
  }

  tags = var.tags
}

# The protected Terraform OIDC identity must be granted Key Vault Secrets
# Officer at this vault by the bootstrap operator before the first apply. The
# role is deliberately not granted by this module so a compromised apply
# identity cannot broaden its own data-plane permissions.
resource "azurerm_key_vault_secret" "secrets" {
  for_each = nonsensitive(var.secrets)

  name            = each.key
  value           = each.value
  key_vault_id    = azurerm_key_vault.main.id
  content_type    = "text/plain"
  expiration_date = var.secret_expiration_date
}

# Azure Storage uses this dedicated key through a managed identity. The expiry
# is an operator-controlled rotation deadline, not a timestamp() expression
# that would create an unintended new key version on every plan.
resource "azurerm_key_vault_key" "storage_cmk" {
  name            = "storage-cmk"
  key_vault_id    = azurerm_key_vault.main.id
  key_type        = "RSA-HSM"
  key_size        = 2048
  key_opts        = ["decrypt", "encrypt", "sign", "unwrapKey", "verify", "wrapKey"]
  expiration_date = var.storage_cmk_key_expiration_date
}
