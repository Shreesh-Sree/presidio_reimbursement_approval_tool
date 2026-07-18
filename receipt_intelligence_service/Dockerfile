FROM python:3.14-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /build

RUN apt-get update \
    && apt-get install --no-install-recommends -y tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "uv>=0.6,<1"

COPY pyproject.toml uv.lock /build/
RUN uv sync --frozen --no-dev --no-install-project

COPY receipt_intelligence_service /build/receipt_intelligence_service
RUN uv sync --frozen --no-dev

# --- Runtime ---
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}"

RUN apt-get update \
    && apt-get install --no-install-recommends -y tesseract-ocr \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r app && useradd -r -g app -d /app app

WORKDIR /app
COPY --from=builder --chown=app:app /build/.venv /app/.venv
COPY --from=builder --chown=app:app /build/receipt_intelligence_service /app/receipt_intelligence_service

USER app
EXPOSE 8012

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8012/health')"]

CMD ["sh", "-c", "uvicorn receipt_intelligence_service.api:create_app --factory --host 0.0.0.0 --port ${PORT:-8012}"]
