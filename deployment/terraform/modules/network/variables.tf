variable "name_prefix" {
  type = string
}

variable "vpc_cidr" {
  type = string
}

variable "availability_zones" {
  type = list(string)

  validation {
    condition     = length(var.availability_zones) >= 2
    error_message = "At least two availability zones are required for the RDS subnet group."
  }
}

variable "aws_region" {
  type = string
}

variable "allowed_ingress_cidr" {
  type = string
}

variable "tags" {
  type = map(string)
}
