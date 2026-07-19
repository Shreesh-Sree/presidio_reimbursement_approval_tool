#!/usr/bin/env bash
set -euo pipefail

# Start the three independently persisted advisory services for local work.
# The core API and frontend remain separate processes: see README.md.
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"$root/scripts/check-local-secret-permissions.sh"

# SQLite and unauthenticated local-only behavior are never selected implicitly
# by a production configuration. This launcher makes the local intent explicit.
export AI_REVIEW_ENVIRONMENT="${AI_REVIEW_ENVIRONMENT:-local}"
export AI_REVIEW_PERSISTENCE_BACKEND="${AI_REVIEW_PERSISTENCE_BACKEND:-sqlite}"
export RECEIPT_INTELLIGENCE_ENVIRONMENT="${RECEIPT_INTELLIGENCE_ENVIRONMENT:-local}"
export RECEIPT_INTELLIGENCE_PERSISTENCE_BACKEND="${RECEIPT_INTELLIGENCE_PERSISTENCE_BACKEND:-sqlite}"
export POLICY_ASSISTANT_ENVIRONMENT="${POLICY_ASSISTANT_ENVIRONMENT:-local}"
export POLICY_ASSISTANT_PERSISTENCE_BACKEND="${POLICY_ASSISTANT_PERSISTENCE_BACKEND:-sqlite}"
trap 'kill 0' EXIT INT TERM
(cd "$root/ai_review_service" && uv run uvicorn ai_review_service.api:create_app --factory --host 127.0.0.1 --port 8011) &
(cd "$root/receipt_intelligence_service" && uv run uvicorn receipt_intelligence_service.api:create_app --factory --host 127.0.0.1 --port 8012) &
(cd "$root/policy_assistant_service" && uv run uvicorn policy_assistant_service.api:create_app --factory --host 127.0.0.1 --port 8013) &
wait
