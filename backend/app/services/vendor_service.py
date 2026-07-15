from sqlalchemy.orm import Session
from app.models.vendor import Vendor


def create_vendor(db: Session, name: str, normalized_name: str = None):
    if not normalized_name:
        normalized_name = name.lower().replace(" ", "_")
    vendor = Vendor(name=name, normalized_name=normalized_name)
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


def list_vendors(db: Session):
    return db.query(Vendor).filter(Vendor.is_deleted == False).all()


def get_vendor(db: Session, vendor_id: str):
    return db.query(Vendor).filter(Vendor.id == vendor_id, Vendor.is_deleted == False).first()
