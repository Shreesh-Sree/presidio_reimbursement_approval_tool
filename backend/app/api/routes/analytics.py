"""Role-scoped dashboard analytics."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.analytics_schemas import AnalyticsOverview
from app.core.database import get_db
from app.core.deps import require_permission
from app.services import analytics_service


router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
async def get_overview(
    period_months: int = Query(default=6, ge=1, le=24),
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("report:read")),
):
    try:
        return analytics_service.overview(db, user, period_months=period_months)
    except analytics_service.AnalyticsError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
