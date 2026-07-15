"""Backward-compatible ASGI entrypoint.

Use ``uv run uvicorn app.main:app`` for new deployments.  Keeping this tiny
shim means older developer commands using ``main:app`` now serve the same
modern, migrated API instead of a separate legacy schema and route set.
"""

from app.main import app

__all__ = ["app"]
