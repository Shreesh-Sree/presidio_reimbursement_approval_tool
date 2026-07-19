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

variable "tenant_id" {
  description = "Azure AD tenant ID."
  type        = string
}

variable "tags" {
  description = "Resource tags."
  type        = map(string)
}

variable "secrets" {
  description = "Map of secret names to their values."
  type        = map(string)
  sensitive   = true
}
