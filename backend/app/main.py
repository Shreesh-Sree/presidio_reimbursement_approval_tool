from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.api.routes import (
    approvals,
    attachments,
    auth,
    categories,
    notifications,
    org_chart,
    policies,
    reports,
    roles,
    users,
    vendors,
)

app = FastAPI(title="Reimbursement API", version="1.0.0")

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(roles.router)
app.include_router(org_chart.router)
app.include_router(policies.router)
app.include_router(categories.router)
app.include_router(vendors.router)
app.include_router(reports.router)
app.include_router(attachments.router)
app.include_router(approvals.router)
app.include_router(notifications.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
