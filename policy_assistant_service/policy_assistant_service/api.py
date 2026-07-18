"""Private HTTP API for the standalone policy assistant service."""

from __future__ import annotations

from contextlib import asynccontextmanager
import logging
import re
import secrets
from time import perf_counter
from typing import AsyncIterator
from uuid import uuid4

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import PolicyAssistantSettings
from .contracts import (
    PolicyAskRequest,
    PolicyAskResponse,
    PolicyDocumentIndexRequest,
    PolicyDocumentIndexResponse,
)
from .logging import configure_logging, request_id_context
from .service import EmptyPolicyDocumentError, PolicyAssistantService, UnsafeQuestionError


_REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


def _bearer_guard(service_token: str):
    bearer = HTTPBearer(auto_error=False)

    async def require_service_token(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    ) -> None:
        if credentials is None or not secrets.compare_digest(credentials.credentials, service_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Valid policy assistant service credentials are required",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return require_service_token


def create_app(
    service: PolicyAssistantService | None = None,
    *,
    settings: PolicyAssistantSettings | None = None,
) -> FastAPI:
    """Create an API intentionally separate from the reimbursement FastAPI app."""

    configure_logging()
    logger = logging.getLogger("policy_assistant")
    resolved_settings = settings or PolicyAssistantSettings()
    assistant = service or PolicyAssistantService(resolved_settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info("policy assistant started", extra={"event": "service_started"})
        try:
            yield
        finally:
            logger.info("policy assistant stopped", extra={"event": "service_stopped"})

    app = FastAPI(
        title="Presidio Policy Assistant",
        version="1.0",
        description=(
            "Private, evidence-only policy retrieval. It never approves, rejects, or mutates "
            "reimbursement records."
        ),
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def correlate_request(request: Request, call_next):  # type: ignore[no-untyped-def]
        supplied_id = request.headers.get("X-Request-ID", "")
        request_id = supplied_id if _REQUEST_ID.fullmatch(supplied_id) else str(uuid4())
        reset_token = request_id_context.set(request_id)
        started = perf_counter()
        try:
            response: Response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            logger.info(
                "policy assistant request completed",
                extra={
                    "event": "http_request_completed",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round((perf_counter() - started) * 1_000, 2),
                },
            )
            return response
        except Exception:
            logger.exception(
                "policy assistant request failed",
                extra={"event": "http_request_failed", "method": request.method, "path": request.url.path},
            )
            raise
        finally:
            request_id_context.reset(reset_token)

    # Liveness/readiness expose no policy data and are deliberately usable by a
    # local process manager without sharing the service token.
    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "policy-assistant"}

    @app.get("/ready")
    async def ready() -> dict[str, str]:
        if not assistant.is_ready():
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="index unavailable")
        return {"status": "ready", "persistence": resolved_settings.persistence_backend}

    protected = APIRouter(
        prefix="/v1",
        dependencies=[Depends(_bearer_guard(resolved_settings.service_token.get_secret_value()))],
    )

    @protected.post(
        "/policy-documents",
        response_model=PolicyDocumentIndexResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def index_policy_document(
        request: PolicyDocumentIndexRequest,
    ) -> PolicyDocumentIndexResponse:
        try:
            return assistant.index_document(request)
        except (EmptyPolicyDocumentError, ValueError) as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    @protected.post("/ask", response_model=PolicyAskResponse)
    async def ask_policy(request: PolicyAskRequest) -> PolicyAskResponse:
        try:
            return await assistant.ask(request)
        except (UnsafeQuestionError, ValueError) as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    app.include_router(protected)
    return app
