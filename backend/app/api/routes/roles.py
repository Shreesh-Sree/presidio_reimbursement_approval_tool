"""Role catalogue endpoint used by user administration."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_permission
from app.services import user_service

router = APIRouter(prefix="/api/roles", tags=["roles"])


@router.get("")
def list_roles(
    db: Session = Depends(get_db),
    _current_user: dict[str, object] = Depends(require_permission("user:read")),
):
    roles = user_service.list_roles(db)
    db.commit()
    return roles
