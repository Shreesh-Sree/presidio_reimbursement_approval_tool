FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

RUN pip install --no-cache-dir "uv>=0.6,<1"

COPY pyproject.toml uv.lock /app/
COPY policy_assistant_service /app/policy_assistant_service

RUN uv sync --frozen --no-dev

EXPOSE 8013

CMD ["sh", "-c", "uvicorn policy_assistant_service.api:create_app --factory --host 0.0.0.0 --port ${PORT:-8013}"]
