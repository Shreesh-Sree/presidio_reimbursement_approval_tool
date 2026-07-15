from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import require_permission
from app.services import approval_service

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


@router.get("/queue")
async def approval_queue(db: Session = Depends(get_db), user = Depends(require_permission("report:approve"))):
    return {"queue": []}


@router.post("/{approval_id}/approve")
async def approve(approval_id: str, remarks: str = None, db: Session = Depends(get_db), user = Depends(require_permission("report:approve"))):
    approval = approval_service.approve(db, approval_id, user["user_id"], remarks)
    return {"status": "approved"}
