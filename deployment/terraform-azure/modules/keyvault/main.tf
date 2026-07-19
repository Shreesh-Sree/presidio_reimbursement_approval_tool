resource "azurerm_key_vault" "main" {
  # Key Vault names: 3-24 alphanumeric + hyphens, globally unique
  name                = "${substr(var.name_prefix, 0, 21)}kv"
  resource_group_name = var.resource_group_name
  location            = var.location
  tenant_id           = var.tenant_id
  sku_name            = "standard"

  rbac_authorization_enabled = true
  purge_protection_enabled   = true
  soft_delete_retention_days = 90

  tags = var.tags
}

# The protected Terraform OIDC identity must be granted Key Vault Secrets
# Officer at this vault by the bootstrap operator before the first apply. The
# role is deliberately not granted by this module so a compromised apply
# identity cannot broaden its own data-plane permissions.
resource "azurerm_key_vault_secret" "secrets" {
  for_each = nonsensitive(var.secrets)

  name         = each.key
  value        = each.value
  key_vault_id = azurerm_key_vault.main.id
}
