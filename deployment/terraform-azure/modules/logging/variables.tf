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

variable "retention_days" {
  description = "Log retention period in days."
  type        = number
}

variable "alert_email" {
  description = "Operational alert recipient managed by the protected environment."
  type        = string
}

variable "tags" {
  description = "Resource tags."
  type        = map(string)
}
