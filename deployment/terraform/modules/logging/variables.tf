variable "name_prefix" {
  type = string
}

variable "retention_in_days" {
  type = number
}

variable "tags" {
  type = map(string)
}
