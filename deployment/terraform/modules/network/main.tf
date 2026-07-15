resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-vpc"
  })
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-igw"
  })
}

resource "aws_subnet" "public" {
  for_each = { for index, az in var.availability_zones : index => az }

  vpc_id                  = aws_vpc.this.id
  availability_zone       = each.value
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, each.key)
  map_public_ip_on_launch = false

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-public-${each.value}"
    Tier = "public"
  })
}

resource "aws_subnet" "database" {
  for_each = { for index, az in var.availability_zones : index => az }

  vpc_id            = aws_vpc.this.id
  availability_zone = each.value
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, each.key + 16)

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-database-${each.value}"
    Tier = "database"
  })
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-public-rt"
  })
}

resource "aws_route_table_association" "public" {
  for_each = aws_subnet.public

  subnet_id      = each.value.id
  route_table_id = aws_route_table.public.id
}

# Database subnets deliberately have no default route. This avoids both a NAT
# Gateway charge and an unnecessary outbound path from the database tier.
resource "aws_route_table" "database" {
  vpc_id = aws_vpc.this.id

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-database-rt"
  })
}

resource "aws_route_table_association" "database" {
  for_each = aws_subnet.database

  subnet_id      = each.value.id
  route_table_id = aws_route_table.database.id
}

# Gateway endpoints have no hourly charge. The backend can reach S3 privately
# from its VPC while the public runtime continues to use the Internet Gateway
# for ECR, SSM, Secrets Manager, and certificate issuance.
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.this.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.public.id, aws_route_table.database.id]

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-s3-gateway-endpoint"
  })
}

resource "aws_security_group" "application" {
  name_prefix = "${var.name_prefix}-app-"
  description = "Public HTTPS ingress to the Caddy proxy; no SSH access."
  vpc_id      = aws_vpc.this.id

  dynamic "ingress" {
    for_each = toset([80, 443])
    content {
      description = ingress.value == 80 ? "HTTP certificate challenge and redirect" : "HTTPS API"
      from_port   = ingress.value
      to_port     = ingress.value
      protocol    = "tcp"
      cidr_blocks = [var.allowed_ingress_cidr]
    }
  }

  egress {
    description = "Container image pulls, AWS APIs, SMTP, and optional AI provider calls"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-app-sg"
  })
}

resource "aws_security_group" "database" {
  name_prefix = "${var.name_prefix}-db-"
  description = "PostgreSQL reachable only from the application host security group."
  vpc_id      = aws_vpc.this.id

  ingress {
    description     = "PostgreSQL from application runtime"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.application.id]
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-db-sg"
  })
}
