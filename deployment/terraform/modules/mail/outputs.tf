output "smtp_endpoint" {
  value = "email-smtp.${var.aws_region}.amazonaws.com"
}

output "sender_email" {
  value = "no-reply@${var.domain_name}"
}

output "identity_verification_token" {
  value = aws_ses_domain_identity.this.verification_token
}
