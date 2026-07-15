#!/usr/bin/env bash
set -euo pipefail

root_dir="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
terraform_dir="${TERRAFORM_DIR:-$root_dir/deployment/terraform}"
aws_region="${AWS_REGION:?Set AWS_REGION to the same region used by Terraform.}"

api_base_url="$(terraform -chdir="$terraform_dir" output -raw api_base_url)"
clerk_publishable_key="$(terraform -chdir="$terraform_dir" output -raw clerk_publishable_key)"
clerk_jwt_template="$(terraform -chdir="$terraform_dir" output -raw clerk_jwt_template)"
frontend_bucket="$(terraform -chdir="$terraform_dir" output -raw frontend_bucket_name)"
distribution_id="$(terraform -chdir="$terraform_dir" output -raw cloudfront_distribution_id)"

if [[ -z "$clerk_publishable_key" || -z "$clerk_jwt_template" ]]; then
  echo "Clerk public build configuration is missing from Terraform outputs." >&2
  exit 1
fi

(
  cd "$root_dir/frontend"
  npm ci
  VITE_API_BASE_URL="$api_base_url" \
    VITE_CLERK_PUBLISHABLE_KEY="$clerk_publishable_key" \
    VITE_CLERK_JWT_TEMPLATE="$clerk_jwt_template" \
    npm run build
)

# Fingerprinted Vite assets may remain cached; index.html must revalidate so it
# references each new asset graph immediately after a release.
aws s3 sync "$root_dir/frontend/dist" "s3://$frontend_bucket/" \
  --region "$aws_region" \
  --delete \
  --exclude "index.html" \
  --cache-control "public,max-age=31536000,immutable"

aws s3 cp "$root_dir/frontend/dist/index.html" "s3://$frontend_bucket/index.html" \
  --region "$aws_region" \
  --cache-control "no-cache"

aws cloudfront wait distribution-deployed \
  --region "$aws_region" \
  --id "$distribution_id"

aws cloudfront create-invalidation \
  --region "$aws_region" \
  --distribution-id "$distribution_id" \
  --paths "/*"
