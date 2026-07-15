resource "aws_ecr_repository" "api" {
  name                 = "${var.name_prefix}/api"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-api"
    Service = "reimbursement-api"
  })
}

resource "aws_ecr_repository" "ai_review" {
  name                 = "${var.name_prefix}/ai-review"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-ai-review"
    Service = "advisory-ai-review"
  })
}

# These advisory services are intentionally separate images. Keeping their
# repositories distinct makes their provenance, image retention, and runtime
# permissions independently auditable without adding another compute host.
resource "aws_ecr_repository" "receipt_intelligence" {
  name                 = "${var.name_prefix}/receipt-intelligence"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-receipt-intelligence"
    Service = "receipt-intelligence"
  })
}

resource "aws_ecr_repository" "policy_assistant" {
  name                 = "${var.name_prefix}/policy-assistant"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-policy-assistant"
    Service = "policy-assistant"
  })
}

resource "aws_ecr_lifecycle_policy" "api" {
  repository = aws_ecr_repository.api.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep the five newest API images."
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 5
      }
      action = { type = "expire" }
    }]
  })
}

resource "aws_ecr_lifecycle_policy" "ai_review" {
  repository = aws_ecr_repository.ai_review.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep the five newest AI review images."
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 5
      }
      action = { type = "expire" }
    }]
  })
}

resource "aws_ecr_lifecycle_policy" "receipt_intelligence" {
  repository = aws_ecr_repository.receipt_intelligence.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep the five newest receipt intelligence images."
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 5
      }
      action = { type = "expire" }
    }]
  })
}

resource "aws_ecr_lifecycle_policy" "policy_assistant" {
  repository = aws_ecr_repository.policy_assistant.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep the five newest policy assistant images."
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 5
      }
      action = { type = "expire" }
    }]
  })
}
