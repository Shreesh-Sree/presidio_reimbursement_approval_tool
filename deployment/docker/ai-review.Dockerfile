FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

RUN pip install --no-cache-dir "uv>=0.6,<1"

COPY . /app

# Provider SDKs are installed only inside this isolated container.  The active
# provider still comes from its separate runtime secret; rule-based review
# remains the deterministic default when no provider/key is selected.
RUN uv sync --frozen --no-dev --extra gemini --extra groq

EXPOSE 8011
