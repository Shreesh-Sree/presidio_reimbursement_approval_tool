"""Organization-scoped user administration endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas import UserCreateRequest, UserUpdateRequest
from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import require_permission
from app.services import user_service

router = APIRouter(prefix="/api/users", tags=["users"])


def _scope(current_user: dict[str, object]) -> tuple[UUID, UUID, UUID]:
    return (
        UUID(str(current_user["organization_id"])),
        UUID(str(current_user["department_id"])),
        UUID(str(current_user["user_id"])),
    )


def _raise_service_error(exc: user_service.UserServiceError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(
    request: UserCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict[str, object] = Depends(require_permission("user:create")),
):
    if get_settings().auth_provider == "clerk" and request.password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password fields are unavailable when OAuth-only authentication is enabled",
        )
    organization_id, department_id, _ = _scope(current_user)
    try:
        return user_service.create_user(
            db,
            organization_id=organization_id,
            department_id=department_id,
            email=str(request.email),
            password=request.password,
            full_name=request.full_name,
            role_codes=request.roles,
            manager_id=request.manager_id,
        )
    except user_service.UserServiceError as exc:
        _raise_service_error(exc)


@router.get("")
async def list_users(
    db: Session = Depends(get_db),
    current_user: dict[str, object] = Depends(require_permission("user:read")),
):
    organization_id, _, _ = _scope(current_user)
    return user_service.list_users(db, organization_id)


@router.get("/{user_id}")
async def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict[str, object] = Depends(require_permission("user:read")),
):
    organization_id, _, _ = _scope(current_user)
    try:
        return user_service.get_user(db, user_id, organization_id)
    except user_service.UserServiceError as exc:
        _raise_service_error(exc)


@router.patch("/{user_id}")
async def update_user(
    user_id: UUID,
    request: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: dict[str, object] = Depends(require_permission("user:update")),
):
    if get_settings().auth_provider == "clerk" and request.password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password fields are unavailable when OAuth-only authentication is enabled",
        )
    organization_id, _, _ = _scope(current_user)
    try:
        return user_service.update_user(
            db,
            user_id=user_id,
            organization_id=organization_id,
            changes=request.model_dump(exclude_unset=True),
        )
    except user_service.UserServiceError as exc:
        _raise_service_error(exc)


@router.post("/{user_id}/deactivate")
async def deactivate_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict[str, object] = Depends(require_permission("user:deactivate")),
):
    organization_id, _, actor_user_id = _scope(current_user)
    try:
        return user_service.deactivate_user(
            db,
            user_id=user_id,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
        )
    except user_service.UserServiceError as exc:
        _raise_service_error(exc)
