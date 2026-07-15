output "state_bucket_name" {
  value = aws_s3_bucket.state.bucket
}

output "backend_hcl" {
  value = <<-EOT
    bucket       = "${aws_s3_bucket.state.bucket}"
    key          = "presidio-reimburse/prod/terraform.tfstate"
    region       = "${var.aws_region}"
    encrypt      = true
    use_lockfile = true
  EOT
}
