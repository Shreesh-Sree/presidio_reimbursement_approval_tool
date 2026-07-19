"""Vendor API used by structured policy rules and report line items."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_permission
from app.services import vendor_service


router = APIRouter(prefix="/api/vendors", tags=["vendors"])


class VendorCreateInput(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    normalized_name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=500)


class VendorUpdateInput(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    normalized_name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=500)


def _vendor_error(exc: Exception) -> None:
    if isinstance(exc, vendor_service.VendorNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, vendor_service.VendorConflictError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    raise exc


@router.get("")
def list_vendors(
    db: Session = Depends(get_db),
    user: dict[str, str] = Depends(require_permission("vendor:read")),
):
    return [
        vendor_service.vendor_payload(vendor)
        for vendor in vendor_service.list_vendors(db, user["organization_id"])
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_vendor(
    payload: VendorCreateInput,
    db: Session = Depends(get_db),
    user: dict[str, str] = Depends(require_permission("vendor:manage")),
):
    try:
        return vendor_service.vendor_payload(
            vendor_service.create_vendor(
                db, organization_id=user["organization_id"], **payload.model_dump()
            )
        )
    except Exception as exc:
        _vendor_error(exc)


@router.get("/{vendor_id}")
def get_vendor(
    vendor_id: str,
    db: Session = Depends(get_db),
    user: dict[str, str] = Depends(require_permission("vendor:read")),
):
    try:
        return vendor_service.vendor_payload(
            vendor_service.get_vendor(db, vendor_id, user["organization_id"])
        )
    except Exception as exc:
        _vendor_error(exc)


@router.patch("/{vendor_id}")
def update_vendor(
    vendor_id: str,
    payload: VendorUpdateInput,
    db: Session = Depends(get_db),
    user: dict[str, str] = Depends(require_permission("vendor:manage")),
):
    try:
        changes: dict[str, Any] = payload.model_dump(exclude_unset=True)
        return vendor_service.vendor_payload(
            vendor_service.update_vendor(
                db, vendor_id, organization_id=user["organization_id"], **changes
            )
        )
    except Exception as exc:
        _vendor_error(exc)


@router.delete("/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vendor(
    vendor_id: str,
    db: Session = Depends(get_db),
    user: dict[str, str] = Depends(require_permission("vendor:manage")),
) -> Response:
    try:
        vendor_service.deactivate_vendor(db, vendor_id, user["organization_id"])
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        _vendor_error(exc)
