FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

RUN pip install --no-cache-dir "uv>=0.6,<1"

COPY pyproject.toml uv.lock /app/
COPY ai_review_service /app/ai_review_service

RUN uv sync --frozen --no-dev --extra gemini --extra groq

EXPOSE 8011

CMD ["sh", "-c", "uvicorn ai_review_service.api:create_app --factory --host 0.0.0.0 --port ${PORT:-8011}"]
