resource "aws_ses_domain_identity" "this" {
  domain = var.domain_name
}

resource "aws_route53_record" "ses_verification" {
  zone_id         = var.route53_zone_id
  name            = "_amazonses.${var.domain_name}"
  type            = "TXT"
  ttl             = 600
  records         = [aws_ses_domain_identity.this.verification_token]
  allow_overwrite = true
}

resource "aws_ses_domain_dkim" "this" {
  domain = aws_ses_domain_identity.this.domain
}

resource "aws_route53_record" "dkim" {
  count = 3

  zone_id         = var.route53_zone_id
  name            = "${aws_ses_domain_dkim.this.dkim_tokens[count.index]}._domainkey.${var.domain_name}"
  type            = "CNAME"
  ttl             = 600
  records         = ["${aws_ses_domain_dkim.this.dkim_tokens[count.index]}.dkim.amazonses.com"]
  allow_overwrite = true
}

# A custom MAIL FROM domain improves SPF alignment. SES falls back to the
# default MAIL FROM domain until the DNS records below propagate.
resource "aws_ses_domain_mail_from" "this" {
  domain           = aws_ses_domain_identity.this.domain
  mail_from_domain = "mail.${var.domain_name}"
}

resource "aws_route53_record" "mail_from_mx" {
  zone_id         = var.route53_zone_id
  name            = "mail.${var.domain_name}"
  type            = "MX"
  ttl             = 600
  records         = ["10 feedback-smtp.${var.aws_region}.amazonses.com"]
  allow_overwrite = true
}

resource "aws_route53_record" "mail_from_spf" {
  zone_id         = var.route53_zone_id
  name            = "mail.${var.domain_name}"
  type            = "TXT"
  ttl             = 600
  records         = ["v=spf1 include:amazonses.com ~all"]
  allow_overwrite = true
}
