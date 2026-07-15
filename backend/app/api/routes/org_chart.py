from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import require_permission
from app.services import org_chart_service

router = APIRouter(prefix="/api/org-chart", tags=["org-chart"])


@router.get("")
async def get_org_chart(db: Session = Depends(get_db), user = Depends(require_permission("user:read"))):
    return org_chart_service.build_org_tree(db, "org-id")
