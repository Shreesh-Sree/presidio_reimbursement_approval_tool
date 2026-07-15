"""Private HTTP surface for the isolated receipt-intelligence service."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging
import re
import secrets
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import JSONResponse

from .config import ReceiptIntelligenceSettings
from .contracts import HealthResponse, ReceiptAnalysisRequest, ReceiptAnalysisResponse
from .observability import (
    LOGGER_NAME,
    configure_logging,
    reset_correlation_id,
    set_correlation_id,
)
from .service import ReceiptIntelligenceService, build_service


logger = logging.getLogger(LOGGER_NAME)
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")


def _bearer_guard(service_token: str | None):
    """Require a configured service-to-service bearer token for private routes."""

    bearer = HTTPBearer(auto_error=False)

    async def require_service_token(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    ) -> None:
        if service_token is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Receipt intelligence service authentication is not configured",
            )
        if credentials is None or not secrets.compare_digest(credentials.credentials, service_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Valid receipt intelligence service credentials are required",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return require_service_token


def _request_id(request: Request) -> str:
    supplied = request.headers.get("X-Request-ID", "").strip()
    return supplied if _REQUEST_ID_PATTERN.fullmatch(supplied) else str(uuid4())


def create_app(
    service: ReceiptIntelligenceService | None = None,
    *,
    settings: ReceiptIntelligenceSettings | None = None,
) -> FastAPI:
    """Create an internal API that accepts metadata/text, never receipt file bytes."""

    settings = settings or ReceiptIntelligenceSettings()
    configure_logging(settings.log_level)
    intelligence_service = service or build_service(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            intelligence_service.close()

    app = FastAPI(
        title="Presidio Receipt Intelligence",
        version="1.0",
        description=(
            "Internal deterministic receipt metadata analysis. It accepts no raw files, "
            "does not perform OCR, and persists only scoped SHA-256 digest observations."
        ),
        lifespan=lifespan,
    )
    token_guard = _bearer_guard(settings.service_token)

    @app.exception_handler(RequestValidationError)
    async def safe_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        """Return validation metadata without reflecting supplied receipt text."""

        logger.info("request_validation_failed")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "detail": [
                    {
                        "type": error["type"],
                        "loc": list(error["loc"]),
                        "msg": error["msg"],
                    }
                    for error in exc.errors()
                ]
            },
        )

    @app.middleware("http")
    async def correlate_request(request: Request, call_next):
        correlation_id = _request_id(request)
        token = set_correlation_id(correlation_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = correlation_id
            logger.info(
                "http_request_completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                },
            )
            return response
        except Exception:
            logger.exception(
                "http_request_failed",
                extra={"method": request.method, "path": request.url.path},
            )
            raise
        finally:
            reset_correlation_id(token)

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", service="receipt-intelligence")

    @app.get("/ready", response_model=HealthResponse)
    async def readiness() -> HealthResponse | JSONResponse:
        try:
            if intelligence_service.is_ready():
                return HealthResponse(status="ready", service="receipt-intelligence")
        except Exception:
            logger.exception("readiness_check_failed")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=HealthResponse(status="not_ready", service="receipt-intelligence").model_dump(),
        )

    @app.post(
        "/v1/analyze",
        response_model=ReceiptAnalysisResponse,
        dependencies=[Depends(token_guard)],
    )
    async def analyze_receipt(request: ReceiptAnalysisRequest) -> ReceiptAnalysisResponse:
        """Analyze ephemeral caller metadata/text; suitable for a queue consumer callback."""

        return intelligence_service.analyze(request)

    return app
