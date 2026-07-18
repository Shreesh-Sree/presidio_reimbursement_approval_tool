"""Service for managing user access requests and admin approvals."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.user_access_request import UserAccessRequest
from app.models.organization import Organization


def create_access_request(
    db: Session,
    email: str,
    full_name: str,
    organization_code: str = "DEMO"
) -> UserAccessRequest:
    """Create new access request for email signup."""

    # Get organization
    org = db.execute(
        select(Organization).where(Organization.code == organization_code)
    ).scalar_one()

    # Check if already exists
    existing = db.execute(
        select(UserAccessRequest).where(UserAccessRequest.email == email)
    ).scalar_one_or_none()

    if existing:
        if existing.status == "pending":
            return existing
        raise ValueError("Access request already processed")

    request = UserAccessRequest(
        id=uuid.uuid4(),
        email=email,
        full_name=full_name,
        organization_id=org.id,
        requested_at=datetime.now(timezone.utc),
        status="pending"
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def list_pending_requests(db: Session, organization_id: uuid.UUID) -> list[UserAccessRequest]:
    """List all pending access requests for an organization."""
    return list(db.execute(
        select(UserAccessRequest)
        .where(
            UserAccessRequest.organization_id == organization_id,
            UserAccessRequest.status == "pending"
        )
        .order_by(UserAccessRequest.requested_at.desc())
    ).scalars())


def approve_request(
    db: Session,
    request_id: uuid.UUID,
    admin_user_id: uuid.UUID,
    department_id: uuid.UUID
) -> User:
    """Approve access request and create user account."""

    request = db.get(UserAccessRequest, request_id)
    if not request or request.status != "pending":
        raise ValueError("Request not found or already processed")

    # Create user with pending_approval status
    user = User(
        id=uuid.uuid4(),
        email=request.email,
        full_name=request.full_name,
        username=request.email.split("@")[0],
        employee_number=f"EMP{uuid.uuid4().hex[:6].upper()}",
        organization_id=request.organization_id,
        department_id=department_id,
        status="active",  # Activate immediately after admin approval
        external_auth_subject=None  # Will be set on first login
    )

    db.add(user)

    # Update request
    request.status = "approved"
    request.approved_at = datetime.now(timezone.utc)
    request.approved_by_user_id = admin_user_id
    request.user_id = user.id

    db.commit()
    db.refresh(user)
    return user


def reject_request(
    db: Session,
    request_id: uuid.UUID,
    admin_user_id: uuid.UUID
) -> UserAccessRequest:
    """Reject access request."""

    request = db.get(UserAccessRequest, request_id)
    if not request or request.status != "pending":
        raise ValueError("Request not found or already processed")

    request.status = "rejected"
    request.rejected_at = datetime.now(timezone.utc)
    request.rejected_by_user_id = admin_user_id

    db.commit()
    db.refresh(request)
    return request


def get_pending_count(db: Session, organization_id: uuid.UUID) -> int:
    """Get count of pending access requests."""
    from sqlalchemy import func
    return db.execute(
        select(func.count(UserAccessRequest.id))
        .where(
            UserAccessRequest.organization_id == organization_id,
            UserAccessRequest.status == "pending"
        )
    ).scalar() or 0
