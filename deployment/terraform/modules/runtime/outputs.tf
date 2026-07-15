output "instance_id" {
  value = aws_instance.application.id
}

output "public_ip" {
  value = aws_eip.application.public_ip
}

output "instance_role_arn" {
  value = aws_iam_role.application.arn
}
