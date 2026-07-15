#!/usr/bin/env bash
set -euo pipefail

root_dir="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
terraform_dir="${TERRAFORM_DIR:-$root_dir/deployment/terraform}"
image_tag="${IMAGE_TAG:-stable}"
aws_region="${AWS_REGION:?Set AWS_REGION to the same region used by Terraform.}"
platform="${DOCKER_PLATFORM:-linux/amd64}"

if [[ "$image_tag" != "stable" ]]; then
  echo "This budget deployment intentionally rolls out the mutable stable tag only." >&2
  exit 2
fi

api_repository="$(terraform -chdir="$terraform_dir" output -raw backend_ecr_repository_url)"
ai_repository="$(terraform -chdir="$terraform_dir" output -raw ai_review_ecr_repository_url)"
registry="${api_repository%%/*}"

aws ecr get-login-password --region "$aws_region" \
  | docker login --username AWS --password-stdin "$registry"

docker build --platform "$platform" \
  --file "$root_dir/deployment/docker/backend.Dockerfile" \
  --tag "$api_repository:$image_tag" \
  "$root_dir/backend"

docker build --platform "$platform" \
  --file "$root_dir/deployment/docker/ai-review.Dockerfile" \
  --tag "$ai_repository:$image_tag" \
  "$root_dir/ai_review_service"

docker push "$api_repository:$image_tag"
docker push "$ai_repository:$image_tag"

if [[ "${DEPLOY_RUNTIME:-0}" == "1" ]]; then
  "$root_dir/deployment/scripts/restart-runtime.sh"
fi
