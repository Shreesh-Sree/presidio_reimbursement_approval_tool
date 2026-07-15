"""Vendor normalization and administration services."""

from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.vendor import Vendor


class VendorNotFoundError(LookupError):
    pass


class VendorConflictError(ValueError):
    pass


def normalize_vendor_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")


def _uuid(value: str | uuid.UUID) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except ValueError as exc:
        raise VendorNotFoundError("Invalid vendor id") from exc


def _active_vendor(db: Session, vendor_id: str | uuid.UUID) -> Vendor:
    vendor = db.scalar(
        select(Vendor).where(Vendor.id == _uuid(vendor_id), Vendor.is_deleted.is_(False))
    )
    if vendor is None:
        raise VendorNotFoundError("Vendor not found")
    return vendor


def create_vendor(db: Session, name: str, normalized_name: str | None = None, description: str | None = None) -> Vendor:
    cleaned_name = name.strip()
    normalized = (normalized_name or normalize_vendor_name(cleaned_name)).strip().lower()
    if not cleaned_name or not normalized:
        raise VendorConflictError("Vendor name is required")
    existing = db.scalar(
        select(Vendor).where(
            func.lower(Vendor.normalized_name) == normalized,
            Vendor.is_deleted.is_(False),
        )
    )
    if existing is not None:
        raise VendorConflictError("A vendor with that normalized name already exists")
    vendor = Vendor(name=cleaned_name, normalized_name=normalized, description=description.strip() if description else None)
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


def get_or_create_vendor(db: Session, name: str) -> Vendor:
    """Resolve a policy-rule free-text vendor without duplicating normalization."""

    normalized = normalize_vendor_name(name)
    if not normalized:
        raise VendorConflictError("Vendor name is required")
    existing = db.scalar(
        select(Vendor).where(
            func.lower(Vendor.normalized_name) == normalized,
            Vendor.is_deleted.is_(False),
        )
    )
    if existing is not None:
        return existing
    # This helper participates in the caller's transaction instead of committing.
    vendor = Vendor(name=name.strip(), normalized_name=normalized)
    db.add(vendor)
    db.flush()
    return vendor


def list_vendors(db: Session) -> list[Vendor]:
    return list(
        db.scalars(
            select(Vendor).where(Vendor.is_deleted.is_(False)).order_by(Vendor.name.asc())
        )
    )


def get_vendor(db: Session, vendor_id: str | uuid.UUID) -> Vendor:
    return _active_vendor(db, vendor_id)


def update_vendor(db: Session, vendor_id: str | uuid.UUID, **changes: Any) -> Vendor:
    vendor = _active_vendor(db, vendor_id)
    if "name" in changes and changes["name"] is not None:
        name = str(changes["name"]).strip()
        if not name:
            raise VendorConflictError("Vendor name cannot be empty")
        vendor.name = name
    if "normalized_name" in changes and changes["normalized_name"] is not None:
        normalized = normalize_vendor_name(str(changes["normalized_name"]))
        if not normalized:
            raise VendorConflictError("Vendor normalized name cannot be empty")
        duplicate = db.scalar(
            select(Vendor).where(
                func.lower(Vendor.normalized_name) == normalized,
                Vendor.id != vendor.id,
                Vendor.is_deleted.is_(False),
            )
        )
        if duplicate is not None:
            raise VendorConflictError("A vendor with that normalized name already exists")
        vendor.normalized_name = normalized
    if "description" in changes:
        description = changes["description"]
        vendor.description = str(description).strip() if description else None
    db.commit()
    db.refresh(vendor)
    return vendor


def deactivate_vendor(db: Session, vendor_id: str | uuid.UUID) -> Vendor:
    vendor = _active_vendor(db, vendor_id)
    vendor.is_deleted = True
    db.commit()
    db.refresh(vendor)
    return vendor


def vendor_payload(vendor: Vendor) -> dict[str, Any]:
    return {
        "id": str(vendor.id),
        "name": vendor.name,
        "normalized_name": vendor.normalized_name,
        "description": vendor.description,
    }
