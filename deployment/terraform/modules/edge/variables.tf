variable "name_prefix" {
  type = string
}

variable "app_domain" {
  type = string
}

variable "api_domain" {
  type = string
}

variable "api_ipv4" {
  type = string
}

variable "route53_zone_id" {
  type = string
}

variable "static_bucket_id" {
  type = string
}

variable "static_bucket_arn" {
  type = string
}

variable "static_bucket_regional_domain_name" {
  type = string
}

variable "tags" {
  type = map(string)
}
