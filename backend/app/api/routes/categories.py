from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import require_permission
from app.services import category_service

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.post("")
async def create_category(code: str, name: str, db: Session = Depends(get_db), user = Depends(require_permission("category:manage"))):
    return category_service.create_category(db, code, name)


@router.get("")
async def list_categories(db: Session = Depends(get_db)):
    return category_service.list_categories(db)


@router.get("/{category_id}")
async def get_category(category_id: str, db: Session = Depends(get_db)):
    return category_service.get_category(db, category_id)


@router.patch("/{category_id}")
async def update_category(category_id: str, name: str = None, db: Session = Depends(get_db), user = Depends(require_permission("category:manage"))):
    return category_service.update_category(db, category_id, name=name)
