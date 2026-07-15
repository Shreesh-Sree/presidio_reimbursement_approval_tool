"""Small structured-logging and request-correlation utilities."""

from __future__ import annotations

from contextvars import ContextVar
from datetime import datetime, timezone
import json
import logging


_correlation_id: ContextVar[str] = ContextVar("receipt_correlation_id", default="-")
LOGGER_NAME = "receipt_intelligence"


def set_correlation_id(value: str):
    """Set the current request correlation ID and return its reset token."""

    return _correlation_id.set(value)


def reset_correlation_id(token: object) -> None:
    _correlation_id.reset(token)


def get_correlation_id() -> str:
    return _correlation_id.get()


class JsonFormatter(logging.Formatter):
    """Emit bounded, machine-readable events without receipt content."""

    _safe_fields = (
        "method",
        "path",
        "status_code",
        "finding_count",
        "duplicate",
    )

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
            "correlation_id": get_correlation_id(),
        }
        for field in self._safe_fields:
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, separators=(",", ":"), default=str)


def configure_logging(level: str = "INFO") -> logging.Logger:
    """Configure only the service logger, avoiding changes to the host root logger."""

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level.upper())
    logger.propagate = False
    if not any(getattr(handler, "_receipt_intelligence_handler", False) for handler in logger.handlers):
        handler = logging.StreamHandler()
        handler._receipt_intelligence_handler = True  # type: ignore[attr-defined]
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    return logger
