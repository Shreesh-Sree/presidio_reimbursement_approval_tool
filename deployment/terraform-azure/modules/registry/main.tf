resource "azurerm_container_registry" "main" {
  # ACR names must be alphanumeric only, 5-50 chars
  name                = replace("${var.name_prefix}acr", "-", "")
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "Basic"
  admin_enabled       = false

  tags = var.tags
}
