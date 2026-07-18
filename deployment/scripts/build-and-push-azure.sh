#!/usr/bin/env bash
# Build and push all service images to Azure Container Registry.
#
# Environment variables:
#   ACR_LOGIN_SERVER  - Required. ACR login server (e.g., presidioregistry.azurecr.io)
#   IMAGE_TAG         - Optional. Defaults to git short SHA.
#   DOCKER_PLATFORM   - Optional. Defaults to linux/amd64.
#
# Prerequisites:
#   - Azure CLI installed and authenticated (`az login`)
#   - Docker daemon running

set -euo pipefail

root_dir="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"

acr_login_server="${ACR_LOGIN_SERVER:?Set ACR_LOGIN_SERVER to your Azure Container Registry (e.g., presidioregistry.azurecr.io)}"
image_tag="${IMAGE_TAG:-$(git -C "$root_dir" rev-parse --short HEAD)}"
platform="${DOCKER_PLATFORM:-linux/amd64}"

declare -A services=(
  [presidio-api]="backend"
  [presidio-ai-review]="ai_review_service"
  [presidio-receipt-intelligence]="receipt_intelligence_service"
  [presidio-policy-assistant]="policy_assistant_service"
)

echo "==> Authenticating to ACR: $acr_login_server"
az acr login --name "${acr_login_server%%.*}"

for image_name in "${!services[@]}"; do
  context_dir="${services[$image_name]}"
  full_tag="$acr_login_server/$image_name:$image_tag"
  latest_tag="$acr_login_server/$image_name:latest"

  echo "==> Building $image_name from $context_dir (tag: $image_tag)"
  docker build --platform "$platform" \
    --tag "$full_tag" \
    --tag "$latest_tag" \
    "$root_dir/$context_dir"

  echo "==> Pushing $image_name"
  docker push "$full_tag"
  docker push "$latest_tag"
done

echo "==> All images pushed to $acr_login_server with tag: $image_tag"
