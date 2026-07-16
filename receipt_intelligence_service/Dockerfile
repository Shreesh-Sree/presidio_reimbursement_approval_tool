FROM python:3.14-slim

WORKDIR /app
RUN apt-get update \
    && apt-get install --no-install-recommends -y tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY receipt_intelligence_service ./receipt_intelligence_service
RUN pip install --no-cache-dir .

EXPOSE 8012
CMD ["uvicorn", "receipt_intelligence_service.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8012"]
