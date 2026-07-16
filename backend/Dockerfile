FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

RUN pip install --no-cache-dir "uv>=0.6,<1"

COPY pyproject.toml uv.lock /app/
COPY app /app/app
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini

RUN uv sync --frozen --no-dev

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
