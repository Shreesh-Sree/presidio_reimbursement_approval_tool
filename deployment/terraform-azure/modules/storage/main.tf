resource "azurerm_user_assigned_identity" "customer_managed_key" {
  name                = "${var.name_prefix}-storage-cmk-id"
  resource_group_name = var.resource_group_name
  location            = var.location

  tags = var.tags
}

resource "azurerm_storage_account" "main" {
  # Storage account names: 3-24 lowercase alphanumeric only
  name                              = replace("${var.name_prefix}st", "-", "")
  resource_group_name               = var.resource_group_name
  location                          = var.location
  account_tier                      = "Standard"
  account_replication_type          = "GRS"
  min_tls_version                   = "TLS1_2"
  allow_nested_items_to_be_public   = false
  public_network_access_enabled     = false
  shared_access_key_enabled         = false
  infrastructure_encryption_enabled = true

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.customer_managed_key.id]
  }

  customer_managed_key {
    key_vault_key_id          = var.customer_managed_key_id
    user_assigned_identity_id = azurerm_user_assigned_identity.customer_managed_key.id
  }

  network_rules {
    default_action             = "Deny"
    bypass                     = ["AzureServices"]
    ip_rules                   = []
    virtual_network_subnet_ids = [var.container_apps_subnet_id]
  }

  blob_properties {
    versioning_enabled = true

    delete_retention_policy {
      days = 30
    }

    container_delete_retention_policy {
      days = 30
    }
  }

  queue_properties {
    logging {
      delete                = true
      read                  = true
      write                 = true
      version               = "1.0"
      retention_policy_days = 30
    }
  }

  tags = var.tags
}

resource "azurerm_storage_container" "uploads" {
  # checkov:skip=CKV2_AZURE_21: Blob request logs are sent through modern Azure Monitor diagnostic settings below; Checkov requires legacy Storage Insights, which needs a shared storage key and conflicts with shared_access_key_enabled=false.
  name                  = "uploads"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}

resource "azurerm_role_assignment" "customer_managed_key_crypto_user" {
  scope                = var.key_vault_id
  role_definition_name = "Key Vault Crypto Service Encryption User"
  principal_id         = azurerm_user_assigned_identity.customer_managed_key.principal_id
}

resource "azurerm_private_endpoint" "blob" {
  name                = "${var.name_prefix}-blob-pe"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id

  private_service_connection {
    name                           = "${var.name_prefix}-blob-psc"
    private_connection_resource_id = azurerm_storage_account.main.id
    is_manual_connection           = false
    subresource_names              = ["blob"]
  }

  private_dns_zone_group {
    name                 = "default"
    private_dns_zone_ids = [var.private_dns_zone_id]
  }

  tags = var.tags
}

resource "azurerm_monitor_diagnostic_setting" "blob" {
  name                       = "${var.name_prefix}-blob-diagnostics"
  target_resource_id         = "${azurerm_storage_account.main.id}/blobServices/default"
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "StorageRead"
  }

  enabled_log {
    category = "StorageWrite"
  }

  enabled_log {
    category = "StorageDelete"
  }
}
