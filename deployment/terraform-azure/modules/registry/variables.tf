variable "name_prefix" {
  description = "Resource naming prefix."
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name."
  type        = string
}

variable "location" {
  description = "Azure region."
  type        = string
}

variable "tags" {
  description = "Resource tags."
  type        = map(string)
}

variable "private_endpoint_subnet_id" {
  description = "Dedicated subnet in which the ACR private endpoint is created."
  type        = string
}

variable "private_dns_zone_id" {
  description = "Private DNS zone ID for privatelink.azurecr.io."
  type        = string
}
