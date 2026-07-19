resource "azurerm_container_registry" "main" {
  # checkov:skip=CKV_AZURE_164: Azure Container Registry Docker Content Trust is retired for new registries; immutable digests, Cosign signing/verification, SBOM, and provenance are enforced in deploy-azure.yml.
  # checkov:skip=CKV_AZURE_165: This is an approved single-region topology. Adding an unapproved geo-replica would add cost, DNS, data-residency, and DR obligations.
  # checkov:skip=CKV_AZURE_166: Quarantine would block every CI push until a Defender scan-and-approve/unquarantine release path is operational.
  # checkov:skip=CKV_AZURE_233: Azure zone redundancy is platform-managed in supported regions; this legacy AzureRM setting forces registry replacement and is handled by the documented blue/green registry migration.
  # ACR names must be alphanumeric only, 5-50 chars
  name                          = replace("${var.name_prefix}acr", "-", "")
  resource_group_name           = var.resource_group_name
  location                      = var.location
  sku                           = "Premium"
  admin_enabled                 = false
  anonymous_pull_enabled        = false
  public_network_access_enabled = false
  data_endpoint_enabled         = true
  export_policy_enabled         = false
  quarantine_policy_enabled     = false
  retention_policy_in_days      = 30

  tags = var.tags
}

resource "azurerm_private_endpoint" "main" {
  name                = "${var.name_prefix}-acr-pe"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id

  private_service_connection {
    name                           = "${var.name_prefix}-acr-psc"
    private_connection_resource_id = azurerm_container_registry.main.id
    is_manual_connection           = false
    subresource_names              = ["registry"]
  }

  private_dns_zone_group {
    name                 = "default"
    private_dns_zone_ids = [var.private_dns_zone_id]
  }

  tags = var.tags
}
