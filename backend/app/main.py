from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.database import get_db
from app.core.observability import (
    RequestCorrelationMiddleware,
    SecurityHeadersMiddleware,
    configure_structured_logging,
)
from app.api.routes import (
    analytics,
    approvals,
    attachments,
    auth,
    categories,
    delegations,
    notifications,
    org_chart,
    payments,
    policies,
    receipt_intelligence,
    reports,
    roles,
    users,
    vendors,
    workflows,
)

app = FastAPI(title="Reimbursement API", version="1.0.0")

settings = get_settings()
configure_structured_logging()
app.add_middleware(RequestCorrelationMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID", "X-Visitor-ID"],
    expose_headers=["X-Request-ID"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(roles.router)
app.include_router(org_chart.router)
app.include_router(policies.router)
app.include_router(categories.router)
app.include_router(delegations.router)
app.include_router(vendors.router)
app.include_router(reports.router)
app.include_router(receipt_intelligence.router)
app.include_router(attachments.router)
app.include_router(approvals.router)
app.include_router(notifications.router)
app.include_router(workflows.router)
app.include_router(payments.router)
app.include_router(analytics.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/ready")
async def ready(db: Session = Depends(get_db)):
    """Verify the core datastore is reachable without leaking connection data."""

    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database is unavailable") from exc
    return {"status": "ready"}
