output "uploads_bucket_name" {
  value = aws_s3_bucket.uploads.bucket
}

output "uploads_bucket_arn" {
  value = aws_s3_bucket.uploads.arn
}

output "static_bucket_name" {
  value = aws_s3_bucket.static.bucket
}

output "static_bucket_id" {
  value = aws_s3_bucket.static.id
}

output "static_bucket_arn" {
  value = aws_s3_bucket.static.arn
}

output "static_bucket_regional_domain_name" {
  value = aws_s3_bucket.static.bucket_regional_domain_name
}
