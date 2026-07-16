# Receipt intelligence service

AWS-hosted isolated receipt analysis service. Its Docker image includes Tesseract OCR. It returns advisory findings only; the core API controls all workflow decisions.

```bash
uv sync
uv run pytest -q
```
