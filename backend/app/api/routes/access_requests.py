"""API routes for user access request management."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, EmailStr
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_permission
from app.services import access_request_service


router = APIRouter(prefix="/access-requests", tags=["access-requests"])


class AccessRequestCreate(BaseModel):
    email: EmailStr
    full_name: str
    organization_code: str = "DEMO"


class AccessRequestApprove(BaseModel):
    department_id: uuid.UUID


class AccessRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    requested_at: str
    status: str

@router.post("", response_model=AccessRequestResponse)
def create_access_request(
    payload: AccessRequestCreate,
    db: Session = Depends(get_db)
):
    """Public endpoint for users to request access."""
    try:
        request = access_request_service.create_access_request(
            db,
            email=payload.email,
            full_name=payload.full_name,
            organization_code=payload.organization_code
        )
        return AccessRequestResponse(
            id=request.id,
            email=request.email,
            full_name=request.full_name,
            requested_at=request.requested_at.isoformat(),
            status=request.status
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[AccessRequestResponse])
def list_pending_requests(
    db: Session = Depends(get_db),
    user: dict = Depends(require_permission("user:manage"))
):
    """Admin endpoint to list pending access requests."""
    requests = access_request_service.list_pending_requests(
        db, user["organization_id"]
    )
    return [
        AccessRequestResponse(
            id=r.id,
            email=r.email,
            full_name=r.full_name,
            requested_at=r.requested_at.isoformat(),
            status=r.status
        )
        for r in requests
    ]


@router.post("/{request_id}/approve")
def approve_request(
    request_id: uuid.UUID,
    payload: AccessRequestApprove,
    db: Session = Depends(get_db),
    user: dict = Depends(require_permission("user:manage"))
):
    """Admin endpoint to approve access request."""
    try:
        created_user = access_request_service.approve_request(
            db,
            request_id,
            user["id"],
            payload.department_id
        )
        return {"message": "Access approved", "user_id": str(created_user.id)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{request_id}/reject")
def reject_request(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: dict = Depends(require_permission("user:manage"))
):
    """Admin endpoint to reject access request."""
    try:
        request = access_request_service.reject_request(
            db, request_id, user["id"]
        )
        return {"message": "Access rejected", "request_id": str(request.id)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/count")
def get_pending_count(
    db: Session = Depends(get_db),
    user: dict = Depends(require_permission("user:manage"))
):
    """Get count of pending access requests for dashboard badge."""
    count = access_request_service.get_pending_count(db, user["organization_id"])
    return {"count": count}
