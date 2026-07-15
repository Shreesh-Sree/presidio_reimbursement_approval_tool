variable "name_prefix" {
  type = string
}

variable "notification_email" {
  type = string
}

variable "instance_id" {
  type = string
}

variable "database_identifier" {
  type = string
}

variable "tags" {
  type = map(string)
}
