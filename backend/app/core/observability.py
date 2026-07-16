"""Low-cost request correlation and structured, privacy-safe application logs."""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Callable
from uuid import uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send


_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{8,128}$")
logger = logging.getLogger("presidio.api")


class JsonLogFormatter(logging.Formatter):
    """Emit a small JSON event without request bodies, headers, or identities."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("request_id", "method", "path", "status_code", "duration_ms"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, separators=(",", ":"), default=str)


def configure_structured_logging() -> None:
    """Configure one process-local JSON handler without duplicating handlers."""

    if any(getattr(handler, "_presidio_structured", False) for handler in logger.handlers):
        return
    handler = logging.StreamHandler()
    handler._presidio_structured = True  # type: ignore[attr-defined]
    handler.setFormatter(JsonLogFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def request_id_from_headers(scope: Scope) -> str:
    headers = {key.decode("latin-1").lower(): value.decode("latin-1") for key, value in scope.get("headers", [])}
    candidate = headers.get("x-request-id", "").strip()
    return candidate if _SAFE_REQUEST_ID.fullmatch(candidate) else uuid4().hex


class RequestCorrelationMiddleware:
    """Attach an opaque request ID and log only operational request metadata."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = request_id_from_headers(scope)
        started = time.perf_counter()
        status_code = 500

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                headers = list(message.get("headers", []))
                headers = [(key, value) for key, value in headers if key.lower() != b"x-request-id"]
                headers.append((b"x-request-id", request_id.encode("ascii")))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            logger.info(
                "request_completed",
                extra={
                    "request_id": request_id,
                    "method": scope.get("method"),
                    "path": scope.get("path"),
                    "status_code": status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
            )


class SecurityHeadersMiddleware:
    """Attach conservative browser security headers to every API response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        async def send_with_security_headers(message: Message) -> None:
            if scope["type"] == "http" and message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                names = {key.lower() for key, _ in headers}
                defaults = {
                    b"x-content-type-options": b"nosniff",
                    b"x-frame-options": b"DENY",
                    b"referrer-policy": b"no-referrer",
                    b"permissions-policy": b"camera=(), microphone=(), geolocation=()",
                    b"content-security-policy": b"default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
                }
                headers.extend((key, value) for key, value in defaults.items() if key not in names)
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_security_headers)
