terraform {
  # Cross-variable validation of email settings requires Terraform 1.9+.
  required_version = ">= 1.9.0"

  # Backend coordinates are intentionally supplied at init time from the
  # protected deployment environment. Never put state access credentials or a
  # storage-account name for a live environment in source control.
  backend "azurerm" {}

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}
