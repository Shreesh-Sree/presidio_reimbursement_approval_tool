FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

RUN pip install --no-cache-dir "uv>=0.6,<1"

COPY . /app

# Production dependencies are resolved from the committed lock file. The
# command is intentionally supplied by Docker Compose so migrations run before
# the one supported API process starts.
RUN uv sync --frozen --no-dev

EXPOSE 8000
