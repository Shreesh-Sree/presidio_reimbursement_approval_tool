variable "aws_region" {
  description = "Region for encrypted Terraform state. Keep this aligned with the workload region."
  type        = string
  default     = "us-east-1"
}

variable "state_bucket_name" {
  description = "Globally unique bucket name for Terraform state."
  type        = string
}
