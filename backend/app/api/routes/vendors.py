from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services import vendor_service

router = APIRouter(prefix="/api/vendors", tags=["vendors"])


@router.post("")
async def create_vendor(name: str, db: Session = Depends(get_db)):
    return vendor_service.create_vendor(db, name)


@router.get("")
async def list_vendors(db: Session = Depends(get_db)):
    return vendor_service.list_vendors(db)


@router.get("/{vendor_id}")
async def get_vendor(vendor_id: str, db: Session = Depends(get_db)):
    return vendor_service.get_vendor(db, vendor_id)
