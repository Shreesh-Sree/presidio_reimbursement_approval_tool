data "aws_iam_policy_document" "assume_ec2" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "application" {
  name               = "${var.name_prefix}-runtime"
  assume_role_policy = data.aws_iam_policy_document.assume_ec2.json

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-runtime-role"
  })
}

data "aws_iam_policy_document" "application" {
  statement {
    sid     = "ReadScopedRuntimeSecrets"
    effect  = "Allow"
    actions = ["secretsmanager:GetSecretValue"]
    resources = [
      var.application_secret_arn,
      var.ai_review_secret_arn,
      var.receipt_intelligence_secret_arn,
      var.policy_assistant_secret_arn,
    ]
  }

  statement {
    sid       = "ListUploadsBucket"
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = [var.uploads_bucket_arn]
  }

  statement {
    sid    = "ReadWriteApplicationUploads"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = ["${var.uploads_bucket_arn}/*"]
  }

  statement {
    sid       = "GetEcrAuthorizationToken"
    effect    = "Allow"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid    = "PullApplicationImages"
    effect = "Allow"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer",
    ]
    resources = [
      var.api_repository_arn,
      var.ai_repository_arn,
      var.receipt_intelligence_repository_arn,
      var.policy_assistant_repository_arn,
    ]
  }

  statement {
    sid    = "WriteContainerLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:DescribeLogStreams",
      "logs:PutLogEvents",
    ]
    resources = [
      "${var.api_log_group_arn}:*",
      "${var.ai_log_group_arn}:*",
      "${var.receipt_intelligence_log_group_arn}:*",
      "${var.policy_assistant_log_group_arn}:*",
      "${var.proxy_log_group_arn}:*",
    ]
  }
}

resource "aws_iam_role_policy" "application" {
  name   = "${var.name_prefix}-runtime-least-privilege"
  role   = aws_iam_role.application.id
  policy = data.aws_iam_policy_document.application.json
}

# Session Manager removes the need to expose SSH or distribute an EC2 key pair.
resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.application.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "application" {
  name = "${var.name_prefix}-runtime"
  role = aws_iam_role.application.name
}

resource "aws_eip" "application" {
  domain = "vpc"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-api-ip"
  })
}

resource "aws_instance" "application" {
  ami                         = var.ami_id
  instance_type               = var.instance_type
  subnet_id                   = var.public_subnet_id
  iam_instance_profile        = aws_iam_instance_profile.application.name
  vpc_security_group_ids      = [var.app_security_group_id]
  user_data_replace_on_change = false

  user_data = templatefile("${path.module}/templates/user_data.sh.tftpl", {
    aws_region                      = var.aws_region
    application_secret_arn          = var.application_secret_arn
    ai_review_secret_arn            = var.ai_review_secret_arn
    receipt_intelligence_secret_arn = var.receipt_intelligence_secret_arn
    policy_assistant_secret_arn     = var.policy_assistant_secret_arn
    ecr_registry_url                = var.ecr_registry_url
    docker_compose = templatefile("${path.module}/templates/docker-compose.yml.tftpl", {
      api_image                           = "${var.api_repository_url}:stable"
      ai_image                            = "${var.ai_repository_url}:stable"
      receipt_intelligence_image          = "${var.receipt_intelligence_repository_url}:stable"
      policy_assistant_image              = "${var.policy_assistant_repository_url}:stable"
      api_log_group_name                  = var.api_log_group_name
      ai_log_group_name                   = var.ai_log_group_name
      receipt_intelligence_log_group_name = var.receipt_intelligence_log_group_name
      policy_assistant_log_group_name     = var.policy_assistant_log_group_name
      proxy_log_group_name                = var.proxy_log_group_name
      aws_region                          = var.aws_region
    })
    caddyfile = templatefile("${path.module}/templates/Caddyfile.tftpl", {
      api_domain = var.api_domain
      acme_email = var.acme_email
    })
  })

  root_block_device {
    encrypted   = true
    volume_type = "gp3"
    volume_size = var.root_volume_gib
    tags = merge(var.tags, {
      Name = "${var.name_prefix}-runtime-root"
    })
  }

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
    # The FastAPI container uses the EC2 role for S3. The user-data firewall
    # rule explicitly blocks the AI container's fixed bridge address from IMDS.
    http_put_response_hop_limit = 2
  }

  lifecycle {
    # Image releases are rolled out through the SSM helper, preserving the
    # advisory service's own encrypted local datastore on this small host.
    ignore_changes = [user_data]
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-runtime"
    Tier = "application"
  })

  depends_on = [
    aws_iam_role_policy.application,
    aws_iam_role_policy_attachment.ssm,
  ]
}

resource "aws_eip_association" "application" {
  allocation_id = aws_eip.application.id
  instance_id   = aws_instance.application.id
}
