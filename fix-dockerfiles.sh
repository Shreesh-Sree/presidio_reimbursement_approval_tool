#!/bin/bash
set -e

# Fix CMD in all microservice Dockerfiles
sed -i 's|CMD \["sh", "-c", "uvicorn policy_assistant_service.api:create_app --factory --host 0.0.0.0 --port \${PORT:-8013}"\]|CMD ["python", "-m", "uvicorn", "policy_assistant_service.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8013"]|' policy_assistant_service/Dockerfile

sed -i 's|CMD \["sh", "-c", "uvicorn ai_review_service.api:create_app --factory --host 0.0.0.0 --port \${PORT:-8011}"\]|CMD ["python", "-m", "uvicorn", "ai_review_service.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8011"]|' ai_review_service/Dockerfile

sed -i 's|CMD \["sh", "-c", "uvicorn receipt_intelligence_service.api:create_app --factory --host 0.0.0.0 --port \${PORT:-8012}"\]|CMD ["python", "-m", "uvicorn", "receipt_intelligence_service.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8012"]|' receipt_intelligence_service/Dockerfile

echo "✓ Fixed all Dockerfiles"
