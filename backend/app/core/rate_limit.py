"""In-memory sliding-window rate limiter for authentication endpoints.

Protects login/bootstrap from brute-force without an external dependency.
State is per-process; behind multiple replicas an attacker gets N * limit
attempts — acceptable for an internal tool with Supabase as primary IdP.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Callable

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

_RATE_LIMITED_PREFIXES = ("/api/auth/login", "/api/auth/bootstrap")
_DEFAULT_LIMIT = 10
_DEFAULT_WINDOW_SECONDS = 60


class RateLimitMiddleware:
    """Sliding-window rate limiter keyed on client IP for sensitive paths."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        enabled: bool = True,
        limit: int = _DEFAULT_LIMIT,
        window_seconds: int = _DEFAULT_WINDOW_SECONDS,
        key_func: Callable[[Scope], str] | None = None,
    ) -> None:
        self.app = app
        self.enabled = enabled
        self.limit = limit
        self.window_seconds = window_seconds
        self.key_func = key_func or self._default_key
        self._hits: dict[str, list[float]] = defaultdict(list)

    @staticmethod
    def _default_key(scope: Scope) -> str:
        headers = dict(scope.get("headers", []))
        forwarded = headers.get(b"x-forwarded-for", b"").decode("latin-1").split(",")[0].strip()
        if forwarded:
            return forwarded
        client = scope.get("client")
        return client[0] if client else "unknown"

    def _is_rate_limited(self, scope: Scope) -> bool:
        path: str = scope.get("path", "")
        if not any(path.startswith(prefix) for prefix in _RATE_LIMITED_PREFIXES):
            return False
        if scope.get("method", "GET") != "POST":
            return False

        key = self.key_func(scope)
        now = time.monotonic()
        window_start = now - self.window_seconds

        hits = self._hits[key]
        self._hits[key] = [t for t in hits if t > window_start]
        if len(self._hits[key]) >= self.limit:
            return True
        self._hits[key].append(now)
        return False

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not self.enabled:
            await self.app(scope, receive, send)
            return

        if self._is_rate_limited(scope):
            response = JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Try again later."},
                headers={"Retry-After": str(self.window_seconds)},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
