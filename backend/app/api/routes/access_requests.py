"""API routes for user access request management."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_permission
from app.services import access_request_service


router = APIRouter(prefix="/access-requests", tags=["access-requests"])


class AccessRequestCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)


class AccessRequestApprove(BaseModel):
    department_id: uuid.UUID


class AccessRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    requested_at: str
    status: str


class AccessRequestAcknowledgement(BaseModel):
    status: str = "received"

@router.post("", response_model=AccessRequestAcknowledgement, status_code=status.HTTP_202_ACCEPTED)
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
        )
        # Do not reveal whether the email already has an account/request.
        return AccessRequestAcknowledgement()
    except ValueError as e:
        raise HTTPException(status_code=422, detail="Unable to accept access request") from e


@router.get("", response_model=list[AccessRequestResponse])
def list_pending_requests(
    db: Session = Depends(get_db),
    user: dict = Depends(require_permission("access_request:manage"))
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
    user: dict = Depends(require_permission("access_request:manage"))
):
    """Admin endpoint to approve access request."""
    try:
        created_user = access_request_service.approve_request(
            db,
            request_id,
            uuid.UUID(str(user["user_id"])),
            uuid.UUID(str(user["organization_id"])),
            payload.department_id
        )
        return {"message": "Access approved", "user_id": str(created_user.id)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{request_id}/reject")
def reject_request(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: dict = Depends(require_permission("access_request:manage"))
):
    """Admin endpoint to reject access request."""
    try:
        request = access_request_service.reject_request(
            db,
            request_id,
            uuid.UUID(str(user["user_id"])),
            uuid.UUID(str(user["organization_id"])),
        )
        return {"message": "Access rejected", "request_id": str(request.id)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/count")
def get_pending_count(
    db: Session = Depends(get_db),
    user: dict = Depends(require_permission("access_request:manage"))
):
    """Get count of pending access requests for dashboard badge."""
    count = access_request_service.get_pending_count(db, user["organization_id"])
    return {"count": count}
