variable "name_prefix" {
  type = string
}

variable "ami_id" {
  type = string
}

variable "instance_type" {
  type = string
}

variable "root_volume_gib" {
  type = number
}

variable "public_subnet_id" {
  type = string
}

variable "app_security_group_id" {
  type = string
}

variable "application_secret_arn" {
  type = string
}

variable "ai_review_secret_arn" {
  type = string
}

variable "uploads_bucket_arn" {
  type = string
}

variable "api_repository_arn" {
  type = string
}

variable "ai_repository_arn" {
  type = string
}

variable "api_repository_url" {
  type = string
}

variable "ai_repository_url" {
  type = string
}

variable "ecr_registry_url" {
  type = string
}

variable "aws_region" {
  type = string
}

variable "api_domain" {
  type = string
}

variable "acme_email" {
  type = string
}

variable "api_log_group_name" {
  type = string
}

variable "ai_log_group_name" {
  type = string
}

variable "proxy_log_group_name" {
  type = string
}

variable "api_log_group_arn" {
  type = string
}

variable "ai_log_group_arn" {
  type = string
}

variable "proxy_log_group_arn" {
  type = string
}

variable "tags" {
  type = map(string)
}
