"""Service for managing user access requests and admin approvals."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.department import Department
from app.models.role import Role
from app.models.user import User
from app.models.user_access_request import UserAccessRequest
from app.models.user_role import UserRole
from app.models.organization import Organization
from app.services import user_service
from app.services.audit_service import record_audit


def create_access_request(
    db: Session,
    email: str,
    full_name: str,
    organization_code: str | None = None,
) -> UserAccessRequest:
    """Create new access request for email signup."""

    normalized_email = email.strip().lower()
    normalized_name = " ".join(full_name.split())
    if not normalized_email or not 2 <= len(normalized_name) <= 255:
        raise ValueError("Invalid access request")

    # Public signup must always use the configured tenant. Allowing callers to
    # select an organization would make it possible to inject requests into a
    # different tenant.
    organization_code = organization_code or get_settings().default_organization_code
    org = db.execute(
        select(Organization).where(Organization.code == organization_code)
    ).scalar_one()

    # Check if already exists
    existing = db.execute(
        select(UserAccessRequest).where(UserAccessRequest.email == normalized_email)
    ).scalar_one_or_none()

    if existing:
        # The public endpoint deliberately returns the same acknowledgement
        # for pending, approved, rejected, and existing-user states.
        return existing

    existing_user = db.scalar(
        select(User.id).where(User.email == normalized_email, User.is_deleted.is_(False))
    )
    if existing_user is not None:
        # Do not create a second tenant entry or disclose that an account
        # exists.  The route still returns the generic acknowledgement.
        return UserAccessRequest(
            email=normalized_email,
            full_name=normalized_name,
            organization_id=org.id,
            requested_at=datetime.now(timezone.utc),
            status="received",
        )

    request = UserAccessRequest(
        id=uuid.uuid4(),
        email=normalized_email,
        full_name=normalized_name,
        organization_id=org.id,
        requested_at=datetime.now(timezone.utc),
        status="pending"
    )
    db.add(request)
    
    # Notify administrators
    from app.services import notification_service
    from app.models.user_role import UserRole
    from app.models.role import Role
    admin_role_ids = db.scalars(
        select(Role.id).where(Role.code.in_(["admin", "administrator"]))
    ).all()
    if admin_role_ids:
        admin_user_ids = db.scalars(
            select(UserRole.user_id).where(UserRole.role_id.in_(admin_role_ids))
        ).all()
        for admin_id in admin_user_ids:
            notification_service.notify(
                db,
                recipient_id=admin_id,
                template_code="access_request_created",
                payload={
                    "title": "New Access Request",
                    "body": f"User {normalized_name} ({normalized_email}) requested access.",
                    "request_id": str(request.id),
                    "email": normalized_email,
                    "full_name": normalized_name,
                }
            )

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
    admin_organization_id: uuid.UUID,
    department_id: uuid.UUID
) -> User:
    """Approve access request and create user account."""

    request = db.get(UserAccessRequest, request_id)
    if not request or request.status != "pending":
        raise ValueError("Request not found or already processed")
    if request.organization_id != admin_organization_id:
        raise ValueError("Request does not belong to your organization")

    department = db.get(Department, department_id)
    if (
        not department
        or department.organization_id != request.organization_id
        or department.is_deleted
        or department.status != "active"
    ):
        raise ValueError("Select an active department in the request organization")

    user_service.ensure_system_roles_and_permissions(db)
    employee_role = db.scalar(
        select(Role).where(
            Role.code == "employee",
            Role.is_active.is_(True),
            Role.is_deleted.is_(False),
        )
    )
    if employee_role is None:
        raise ValueError("Employee role is not configured")

    # Approved requests become normal employees so the user can sign in and
    # access the employee features immediately.
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
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=employee_role.id))

    # Update request
    request.status = "approved"
    request.approved_at = datetime.now(timezone.utc)
    request.approved_by_user_id = admin_user_id
    request.user_id = user.id
    record_audit(
        db,
        "user_access_requests",
        str(request.id),
        "approved",
        after={"user_id": str(user.id), "organization_id": str(request.organization_id)},
        performed_by=str(admin_user_id),
    )

    db.commit()
    db.refresh(user)
    return user


def reject_request(
    db: Session,
    request_id: uuid.UUID,
    admin_user_id: uuid.UUID,
    admin_organization_id: uuid.UUID,
) -> UserAccessRequest:
    """Reject access request."""

    request = db.get(UserAccessRequest, request_id)
    if not request or request.status != "pending":
        raise ValueError("Request not found or already processed")
    if request.organization_id != admin_organization_id:
        raise ValueError("Request does not belong to your organization")

    request.status = "rejected"
    request.rejected_at = datetime.now(timezone.utc)
    request.rejected_by_user_id = admin_user_id
    record_audit(
        db,
        "user_access_requests",
        str(request.id),
        "rejected",
        performed_by=str(admin_user_id),
    )

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
