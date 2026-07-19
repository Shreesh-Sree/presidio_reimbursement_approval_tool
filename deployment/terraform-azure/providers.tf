provider "azurerm" {
  features {}

  subscription_id = var.subscription_id
  # Storage account keys are disabled; all Terraform Storage data-plane calls
  # must use the deployment identity's Azure AD/RBAC permissions instead.
  storage_use_azuread = true
}
