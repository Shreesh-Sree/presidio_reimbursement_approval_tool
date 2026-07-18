FROM python:3.14-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /build

RUN pip install --no-cache-dir "uv>=0.6,<1"

COPY pyproject.toml uv.lock /build/
RUN uv sync --frozen --no-dev --no-install-project

COPY app /build/app
COPY alembic /build/alembic
COPY alembic.ini /build/alembic.ini

RUN uv sync --frozen --no-dev

# --- Runtime ---
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}"

RUN groupadd -r app && useradd -r -g app -d /app app

WORKDIR /app
COPY --from=builder --chown=app:app /build/.venv /app/.venv
COPY --from=builder --chown=app:app /build/app /app/app
COPY --from=builder --chown=app:app /build/alembic /app/alembic
COPY --from=builder --chown=app:app /build/alembic.ini /app/alembic.ini

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"]

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
