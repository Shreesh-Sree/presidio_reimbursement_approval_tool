"""Authentication endpoints, including the one-time first-admin bootstrap."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.schemas import BootstrapRequest, LoginRequest
from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import create_access_token, decode_token, verify_password
from app.models.department import Department
from app.models.organization import Organization
from app.models.session import Session as AuthSession
from app.models.user import User
from app.services import user_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "backend"}



def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _require_local_auth() -> None:
    """Disable password bootstrap/login whenever Supabase is the configured IdP."""

    if get_settings().auth_provider != "local":
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={
                "code": "oauth_only",
                "message": "Password authentication is disabled. Sign in through your company OAuth provider.",
            },
        )


def _expiry_for_token(token: str) -> datetime:
    payload = decode_token(token)
    expiry = payload.get("exp") if payload else None
    if isinstance(expiry, (int, float)):
        return datetime.fromtimestamp(expiry, UTC)
    # ``create_access_token`` always includes exp; retaining a defensive
    # fallback makes a malformed token fail via the normal session check.
    return datetime.now(UTC)


def _session_user_payload(db: Session, user: User) -> dict[str, object]:
    return {
        "user_id": str(user.id),
        "email": user.email,
        "organization_id": str(user.organization_id),
        "department_id": str(user.department_id),
        "roles": user_service.role_codes_for_user(db, user.id),
        "permissions": user_service.permission_codes_for_user(db, user.id),
    }


def _issue_login_response(db: Session, user: User) -> dict[str, object]:
    # ``jti`` makes each login independently revocable, even if two logins
    # happen within the same JWT timestamp second.
    token = create_access_token({"sub": str(user.id), "email": user.email, "jti": uuid4().hex})
    auth_session = AuthSession(
        user_id=user.id,
        session_token_hash=_token_hash(token),
        expires_at=_expiry_for_token(token),
    )
    user.last_login_at = datetime.now(UTC)
    db.add(auth_session)
    db.commit()
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": _session_user_payload(db, user),
    }


@router.post("/bootstrap", status_code=status.HTTP_201_CREATED)
def bootstrap(request: BootstrapRequest, db: Session = Depends(get_db)):
    """Create the first organization and administrator in an empty deployment.

    The endpoint intentionally becomes unavailable once an active account
    exists, preventing it from becoming an administrative back door.
    """

    _require_local_auth()
    active_user = db.scalar(
        select(User.id).where(User.is_deleted.is_(False), User.status == "active").limit(1)
    )
    if active_user is not None:
        raise HTTPException(status_code=409, detail="Bootstrap has already been completed")

    org_code_taken = db.scalar(
        select(Organization.id).where(
            Organization.code == request.organization_code,
            Organization.is_deleted.is_(False),
        )
    )
    if org_code_taken is not None:
        raise HTTPException(status_code=409, detail="Organization code already exists")

    organization = Organization(name=request.organization_name, code=request.organization_code)
    db.add(organization)
    db.flush()
    department = Department(
        organization_id=organization.id,
        code=request.department_code,
        name=request.department_name,
    )
    db.add(department)
    db.flush()

    try:
        created = user_service.create_user(
            db,
            organization_id=organization.id,
            department_id=department.id,
            email=str(request.email),
            password=request.password,
            full_name=request.full_name,
            role_codes=["administrator"],
            manager_id=None,
        )
    except user_service.UserServiceError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    administrator = db.scalar(select(User).where(User.id == UUID(str(created["id"]))))
    if administrator is None:  # Defensive: the create service has committed.
        raise HTTPException(status_code=500, detail="Unable to create administrator")
    return _issue_login_response(db, administrator)


@router.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    _require_local_auth()
    user_service.ensure_system_roles_and_permissions(db)
    user = db.scalar(
        select(User).where(
            func.lower(User.email) == str(request.email).lower(),
            User.is_deleted.is_(False),
        )
    )
    try:
        password_is_valid = user is not None and verify_password(request.password, user.password_hash)
    except (TypeError, ValueError):
        password_is_valid = False
    if user is None or user.status != "active" or not password_is_valid:
        # Do not disclose whether an email address exists or an account is inactive.
        db.rollback()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return _issue_login_response(db, user)


@router.post("/logout")
def logout(
    current_user: dict[str, object] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session_id = current_user.get("session_id")
    if session_id:
        auth_session = db.get(AuthSession, session_id)
        if auth_session is not None:
            auth_session.revoked_at = datetime.now(UTC)
            db.commit()
    # Supabase session revocation is owned by the Supabase client.  The local mode
    # retains explicit session revocation for migration/test environments.
    return {"message": "Logged out" if session_id else "OAuth sign-out is managed by the identity provider"}


@router.get("/me")
def get_me(
    current_user: dict[str, object] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if get_settings().auth_provider == "supabase":
        user = current_user.get("model")
        if isinstance(user, User):
            user_service.record_oauth_login(db, user)
    return {
        "user_id": current_user["user_id"],
        "email": current_user["email"],
        "organization_id": current_user["organization_id"],
        "department_id": current_user["department_id"],
        "roles": current_user["roles"],
        "permissions": current_user["permissions"],
    }
