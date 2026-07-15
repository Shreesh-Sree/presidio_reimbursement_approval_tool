FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

RUN pip install --no-cache-dir "uv>=0.6,<1"

COPY . /app

# The optional Gemini adapter is present but dormant without its key; the
# deterministic advisory evaluator remains the safe default.
RUN uv sync --frozen --no-dev --extra gemini

EXPOSE 8011
