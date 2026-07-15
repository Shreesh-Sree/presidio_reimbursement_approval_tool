output "vpc_id" {
  value = aws_vpc.this.id
}

output "public_subnet_ids" {
  value = [for index in sort(keys(aws_subnet.public)) : aws_subnet.public[index].id]
}

output "private_database_subnet_ids" {
  value = [for index in sort(keys(aws_subnet.database)) : aws_subnet.database[index].id]
}

output "application_security_group_id" {
  value = aws_security_group.application.id
}

output "database_security_group_id" {
  value = aws_security_group.database.id
}
