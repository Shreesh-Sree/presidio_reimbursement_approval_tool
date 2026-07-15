"""Authentication and authorization dependencies for API routes."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.session import Session as AuthSession
from app.models.user import User
from app.services import user_service

bearer = HTTPBearer(auto_error=False)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _is_expired(value: datetime) -> bool:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value <= datetime.now(UTC)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Resolve an active user from a signed, non-revoked login session."""

    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(creds.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id = uuid.UUID(str(payload.get("sub")))
    except (TypeError, ValueError, AttributeError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject") from exc

    user = db.scalar(
        select(User).where(
            User.id == user_id,
            User.is_deleted.is_(False),
            User.status == "active",
        )
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    auth_session = db.scalar(
        select(AuthSession).where(
            AuthSession.session_token_hash == _token_hash(creds.credentials),
            AuthSession.user_id == user.id,
            AuthSession.is_deleted.is_(False),
            AuthSession.revoked_at.is_(None),
        )
    )
    if auth_session is None or _is_expired(auth_session.expires_at):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session is no longer active")

    return {
        "user_id": str(user.id),
        "email": user.email,
        "organization_id": str(user.organization_id),
        "department_id": str(user.department_id),
        "roles": user_service.role_codes_for_user(db, user.id),
        "permissions": user_service.permission_codes_for_user(db, user.id),
        "session_id": auth_session.id,
        "model": user,
    }


def require_permission(code: str):
    """Require a permission granted through the authenticated user's roles."""

    async def check_permission(
        user: dict[str, object] = Depends(get_current_user),
    ) -> dict[str, object]:
        permission_codes = set(user["permissions"])
        if "*" not in permission_codes and code not in permission_codes:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing permission: {code}")
        return user

    return check_permission
