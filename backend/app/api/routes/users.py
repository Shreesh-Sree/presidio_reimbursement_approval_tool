from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import require_permission
from app.services import user_service

router = APIRouter(prefix="/api/users", tags=["users"])

@router.post("")
async def create_user(email: str, full_name: str, db: Session = Depends(get_db), user = Depends(require_permission("user:create"))):
    return user_service.create_user(db, email, "password", full_name, "org-id")

@router.get("")
async def list_users(db: Session = Depends(get_db), user = Depends(require_permission("user:read"))):
    return user_service.list_users(db, "org-id")

@router.get("/{user_id}")
async def get_user(user_id: str, db: Session = Depends(get_db), user = Depends(require_permission("user:read"))):
    return user_service.get_user(db, user_id)

@router.post("/{user_id}/deactivate")
async def deactivate_user(user_id: str, db: Session = Depends(get_db), user = Depends(require_permission("user:deactivate"))):
    return user_service.deactivate_user(db, user_id)
