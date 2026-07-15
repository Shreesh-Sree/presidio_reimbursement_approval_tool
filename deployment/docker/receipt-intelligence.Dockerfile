FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

RUN pip install --no-cache-dir "uv>=0.6,<1"

# Copy only the production package and lock inputs. In particular, local test
# caches, virtual environments, and receipt files cannot enter this image.
COPY pyproject.toml uv.lock README.md /app/
COPY receipt_intelligence_service /app/receipt_intelligence_service

RUN uv sync --frozen --no-dev

EXPOSE 8012
