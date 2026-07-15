variable "uploads_bucket_name" {
  type = string
}

variable "static_bucket_name" {
  type = string
}

variable "force_destroy" {
  type = bool
}

variable "tags" {
  type = map(string)
}
