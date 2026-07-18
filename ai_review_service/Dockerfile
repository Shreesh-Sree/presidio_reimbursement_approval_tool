FROM python:3.14-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /build

RUN pip install --no-cache-dir "uv>=0.6,<1"

COPY pyproject.toml uv.lock /build/
RUN uv sync --frozen --no-dev --no-install-project --extra gemini --extra groq

COPY ai_review_service /build/ai_review_service
RUN uv sync --frozen --no-dev --extra gemini --extra groq

# --- Runtime ---
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}"

RUN groupadd -r app && useradd -r -g app -d /app app

WORKDIR /app
COPY --from=builder --chown=app:app /build/.venv /app/.venv
COPY --from=builder --chown=app:app /build/ai_review_service /app/ai_review_service

USER app
EXPOSE 8011

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8011/health')"]

CMD ["sh", "-c", "uvicorn ai_review_service.api:create_app --factory --host 0.0.0.0 --port ${PORT:-8011}"]
