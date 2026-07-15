variable "name_prefix" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "database_security_group_id" {
  type = string
}

variable "availability_zone" {
  type = string
}

variable "instance_class" {
  type = string
}

variable "allocated_storage_gib" {
  type = number
}

variable "max_allocated_storage_gib" {
  type = number
}

variable "engine_version" {
  type     = string
  default  = null
  nullable = true
}

variable "database_name" {
  type    = string
  default = "reimbursement"
}

variable "master_username" {
  type    = string
  default = "app_user"
}

variable "master_password" {
  type      = string
  sensitive = true
}

variable "deletion_protection" {
  type = bool
}

variable "skip_final_snapshot" {
  type = bool
}

variable "tags" {
  type = map(string)
}
