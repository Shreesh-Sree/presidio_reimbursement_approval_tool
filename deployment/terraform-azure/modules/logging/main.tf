resource "azurerm_log_analytics_workspace" "main" {
  name                = "${var.name_prefix}-logs"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "PerGB2018"
  retention_in_days   = var.retention_days

  tags = var.tags
}

resource "azurerm_monitor_action_group" "operations" {
  name                = "${var.name_prefix}-ops"
  resource_group_name = var.resource_group_name
  short_name          = substr(replace(var.name_prefix, "-", ""), 0, 12)

  email_receiver {
    name                    = "operations"
    email_address           = var.alert_email
    use_common_alert_schema = true
  }

  tags = var.tags
}

# The Container Apps system-log table is created after first runtime activity.
# Query validation is therefore deferred to Azure, while the deployment
# runbook requires a staging alert-fire test before production approval.
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "container_app_failures" {
  name                  = "${var.name_prefix}-container-failures"
  resource_group_name   = var.resource_group_name
  location              = var.location
  display_name          = "${var.name_prefix}: Container App failures"
  description           = "Pages operations when Container Apps report restart or provisioning failures."
  scopes                = [azurerm_log_analytics_workspace.main.id]
  severity              = 1
  enabled               = true
  evaluation_frequency  = "PT5M"
  window_duration       = "PT5M"
  skip_query_validation = true

  criteria {
    query                   = <<-KQL
      ContainerAppSystemLogs_CL
      | where TimeGenerated > ago(5m)
      | where Reason_s in ("ContainerCrashing", "Failed", "ProvisioningFailed")
      | summarize FailureCount = count()
    KQL
    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  action {
    action_groups = [azurerm_monitor_action_group.operations.id]
  }

  tags = var.tags
}
