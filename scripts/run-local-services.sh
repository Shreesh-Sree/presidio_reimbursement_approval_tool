#!/usr/bin/env bash
set -euo pipefail

# Start the three independently persisted advisory services for local work.
# The core API and frontend remain separate processes: see README.md.
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
trap 'kill 0' EXIT INT TERM
(cd "$root/ai_review_service" && uv run uvicorn ai_review_service.api:create_app --factory --host 127.0.0.1 --port 8011) &
(cd "$root/receipt_intelligence_service" && uv run uvicorn receipt_intelligence_service.api:create_app --factory --host 127.0.0.1 --port 8012) &
(cd "$root/policy_assistant_service" && uv run uvicorn policy_assistant_service.api:create_app --factory --host 127.0.0.1 --port 8013) &
wait
