resource "azurerm_key_vault" "main" {
  # Key Vault names: 3-24 alphanumeric + hyphens, globally unique
  name                = "${substr(var.name_prefix, 0, 21)}kv"
  resource_group_name = var.resource_group_name
  location            = var.location
  tenant_id           = var.tenant_id
  sku_name            = "standard"

  rbac_authorization_enabled = true
  purge_protection_enabled   = false

  tags = var.tags
}

# Grant the deployer full secret management via RBAC
resource "azurerm_role_assignment" "deployer_secrets_officer" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = var.deployer_object_id
}

# Create all secrets
resource "azurerm_key_vault_secret" "secrets" {
  for_each = nonsensitive(var.secrets)

  name         = each.key
  value        = each.value
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_role_assignment.deployer_secrets_officer]
}
