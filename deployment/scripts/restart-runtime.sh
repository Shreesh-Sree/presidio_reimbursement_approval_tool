#!/usr/bin/env bash
set -euo pipefail

root_dir="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
terraform_dir="${TERRAFORM_DIR:-$root_dir/deployment/terraform}"
aws_region="${AWS_REGION:?Set AWS_REGION to the same region used by Terraform.}"
instance_id="$(terraform -chdir="$terraform_dir" output -raw runtime_instance_id)"

command_id="$(aws ssm send-command \
  --region "$aws_region" \
  --document-name AWS-RunShellScript \
  --instance-ids "$instance_id" \
  --parameters 'commands=["sudo systemctl restart reimbursement-runtime.service"]' \
  --query 'Command.CommandId' \
  --output text)"

aws ssm wait command-executed \
  --region "$aws_region" \
  --command-id "$command_id" \
  --instance-id "$instance_id"

aws ssm get-command-invocation \
  --region "$aws_region" \
  --command-id "$command_id" \
  --instance-id "$instance_id" \
  --output json
