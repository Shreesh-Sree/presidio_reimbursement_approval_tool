"""Run the isolated service with ``python -m receipt_intelligence_service``."""

import uvicorn

from .api import create_app


if __name__ == "__main__":  # pragma: no cover - deployment entry point
    uvicorn.run(create_app(), host="0.0.0.0", port=8012)
