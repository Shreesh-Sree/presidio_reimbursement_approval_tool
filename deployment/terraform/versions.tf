terraform {
  required_version = ">= 1.7.0"

  # Values are supplied from the untracked backend.hcl created after the
  # bootstrap state bucket exists.
  backend "s3" {}

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.83, < 7.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}
