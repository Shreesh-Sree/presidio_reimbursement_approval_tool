resource "azurerm_virtual_network" "main" {
  name                = "${var.name_prefix}-vnet"
  location            = var.location
  resource_group_name = var.resource_group_name
  address_space       = [var.address_space]

  tags = var.tags
}

# The current Container Apps environment is Consumption-only. Azure requires
# this infrastructure subnet to remain undelegated and dedicated to Container
# Apps; it is intentionally separate from private endpoints.
resource "azurerm_subnet" "container_apps" {
  name                 = "container-apps"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [var.container_apps_subnet_address_prefix]
}

resource "azurerm_subnet" "private_endpoints" {
  name                              = "private-endpoints"
  resource_group_name               = var.resource_group_name
  virtual_network_name              = azurerm_virtual_network.main.name
  address_prefixes                  = [var.private_endpoints_subnet_address_prefix]
  private_endpoint_network_policies = "Disabled"
}

# Explicit NSG associations provide a policy boundary while retaining Azure's
# required default platform rules for the Consumption environment and private
# endpoint traffic. Service-specific restrictions follow the documented
# blue/green connectivity smoke test.
resource "azurerm_network_security_group" "container_apps" {
  name                = "${var.name_prefix}-aca-nsg"
  location            = var.location
  resource_group_name = var.resource_group_name

  tags = var.tags
}

resource "azurerm_subnet_network_security_group_association" "container_apps" {
  subnet_id                 = azurerm_subnet.container_apps.id
  network_security_group_id = azurerm_network_security_group.container_apps.id
}

resource "azurerm_network_security_group" "private_endpoints" {
  name                = "${var.name_prefix}-pe-nsg"
  location            = var.location
  resource_group_name = var.resource_group_name

  tags = var.tags
}

resource "azurerm_subnet_network_security_group_association" "private_endpoints" {
  subnet_id                 = azurerm_subnet.private_endpoints.id
  network_security_group_id = azurerm_network_security_group.private_endpoints.id
}

locals {
  private_dns_zones = {
    key_vault = "privatelink.vaultcore.azure.net"
    registry  = "privatelink.azurecr.io"
    blob      = "privatelink.blob.core.windows.net"
  }
}

resource "azurerm_private_dns_zone" "main" {
  for_each = local.private_dns_zones

  name                = each.value
  resource_group_name = var.resource_group_name

  tags = var.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "main" {
  for_each = azurerm_private_dns_zone.main

  name                  = "${var.name_prefix}-${each.key}-dns"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = each.value.name
  virtual_network_id    = azurerm_virtual_network.main.id
  registration_enabled  = false

  tags = var.tags
}
