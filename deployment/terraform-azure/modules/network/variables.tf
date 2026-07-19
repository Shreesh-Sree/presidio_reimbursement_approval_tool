variable "name_prefix" {
  description = "Resource naming prefix."
  type        = string
}

variable "resource_group_name" {
  description = "Resource group that owns the private network."
  type        = string
}

variable "location" {
  description = "Azure region for the virtual network."
  type        = string
}

variable "address_space" {
  description = "CIDR address space reserved for the production private network."
  type        = string
}

variable "container_apps_subnet_address_prefix" {
  description = "Dedicated, undelegated /23-or-larger subnet for the Consumption Container Apps environment."
  type        = string
}

variable "private_endpoints_subnet_address_prefix" {
  description = "Dedicated subnet for private endpoints; size it for registry data endpoints and future growth."
  type        = string
}

variable "tags" {
  description = "Tags applied to network resources."
  type        = map(string)
}
