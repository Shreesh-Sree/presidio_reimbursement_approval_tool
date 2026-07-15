"""Small structured logging utility that never logs document or question bodies."""

from __future__ import annotations

from contextvars import ContextVar
from datetime import UTC, datetime
import json
import logging
from typing import Any


request_id_context: ContextVar[str | None] = ContextVar("policy_assistant_request_id", default=None)


class JsonLogFormatter(logging.Formatter):
    """Emit compact JSON records for correlation without retaining sensitive content."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = request_id_context.get()
        if request_id:
            payload["request_id"] = request_id
        for key in (
            "event",
            "method",
            "path",
            "status_code",
            "duration_ms",
            "tenant_ref",
            "policy_version_ref",
            "chunk_count",
        ):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("policy_assistant")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not any(getattr(handler, "_policy_assistant_handler", False) for handler in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonLogFormatter())
        handler._policy_assistant_handler = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
    return logger
