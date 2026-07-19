FROM python:3.14-slim@sha256:cea0e6040540fb2b965b6e7fb5ffa00871e632eef63719f0ea54bca189ce14a6 AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /build

RUN pip install --no-cache-dir "uv>=0.6,<1"

COPY pyproject.toml uv.lock /build/
RUN uv sync --frozen --no-dev --no-install-project

COPY policy_assistant_service /build/policy_assistant_service
RUN uv sync --frozen --no-dev

# --- Runtime ---
FROM python:3.14-slim@sha256:cea0e6040540fb2b965b6e7fb5ffa00871e632eef63719f0ea54bca189ce14a6

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}"

RUN groupadd -r app && useradd -r -g app -d /app app \
    && install -d -o app -g app /app/var

WORKDIR /app
COPY --from=builder --chown=app:app /build/.venv /app/.venv
COPY --from=builder --chown=app:app /build/policy_assistant_service /app/policy_assistant_service

USER app
EXPOSE 8013

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8013/health')"]

CMD ["python", "-m", "uvicorn", "policy_assistant_service.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8013"]
