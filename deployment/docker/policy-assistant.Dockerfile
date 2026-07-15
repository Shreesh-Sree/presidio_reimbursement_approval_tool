FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

RUN pip install --no-cache-dir "uv>=0.6,<1"

# The assistant image contains only its package and committed dependency lock;
# no core backend code, database configuration, or local development state is
# copied into the isolated runtime.
COPY pyproject.toml uv.lock README.md /app/
COPY policy_assistant_service /app/policy_assistant_service

RUN uv sync --frozen --no-dev

EXPOSE 8013
