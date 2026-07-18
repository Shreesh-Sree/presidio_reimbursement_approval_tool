"""Organization-scoped user administration endpoints."""

from __future__ import annotations

import csv
import io
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.schemas import UserCreateRequest, UserUpdateRequest
from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import require_permission
from app.services import supabase_provisioning_service, user_service

router = APIRouter(prefix="/api/users", tags=["users"])


def _scope(current_user: dict[str, object]) -> tuple[UUID, UUID, UUID]:
    return (
        UUID(str(current_user["organization_id"])),
        UUID(str(current_user["department_id"])),
        UUID(str(current_user["user_id"])),
    )


def _raise_service_error(exc: user_service.UserServiceError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


def _create_user_with_invitation(
    *,
    db: Session,
    organization_id: UUID,
    department_id: UUID,
    request: UserCreateRequest,
) -> dict[str, object]:
    """Keep Supabase Auth and the app allowlist in lockstep for admin-created users."""

    user_service.validate_user_creation(
        db,
        organization_id=organization_id,
        email=str(request.email),
        role_codes=request.roles,
        manager_id=request.manager_id,
    )
    settings = get_settings()
    invitation = None
    if settings.auth_provider == "supabase":
        try:
            invitation = supabase_provisioning_service.invite_user(
                settings=settings,
                email=str(request.email),
                full_name=request.full_name,
                organization_id=str(organization_id),
            )
        except supabase_provisioning_service.SupabaseProvisioningError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
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
    except Exception:
        if invitation is not None:
            supabase_provisioning_service.revoke_invitation(settings=settings, invitation_id=invitation.id)
        raise


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(
    request: UserCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict[str, object] = Depends(require_permission("user:create")),
):
    if get_settings().auth_provider == "supabase" and request.password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password fields are unavailable when OAuth-only authentication is enabled",
        )
    organization_id, department_id, _ = _scope(current_user)
    try:
        return _create_user_with_invitation(
            db=db, organization_id=organization_id, department_id=department_id, request=request
        )
    except user_service.UserServiceError as exc:
        _raise_service_error(exc)


@router.post("/bulk", status_code=status.HTTP_201_CREATED)
async def bulk_create_users(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict[str, object] = Depends(require_permission("user:create")),
):
    """Invite up to 500 users from a CSV without creating passwords.

    Required headers: ``email,full_name,roles``. Roles are semicolon-separated
    codes (for example ``employee;approver``). Rows are isolated so an invalid
    email never prevents valid rows from being imported; every successful row
    uses the existing audited user-creation workflow.
    """

    if file.content_type not in {"text/csv", "application/vnd.ms-excel", "application/csv"}:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Upload a CSV file")
    raw = await file.read()
    if len(raw) > 1_000_000:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="CSV must be 1 MB or smaller")
    try:
        rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    except (UnicodeDecodeError, csv.Error) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="CSV could not be read") from exc
    if not rows or len(rows) > 500:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="CSV must contain 1 to 500 user rows")
    required = {"email", "full_name", "roles"}
    if not required.issubset(set(rows[0])):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="CSV headers must include email, full_name, roles")
    organization_id, department_id, _ = _scope(current_user)
    created: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []
    for row_number, row in enumerate(rows, start=2):
        try:
            request = UserCreateRequest(
                email=(row.get("email") or "").strip(),
                full_name=(row.get("full_name") or "").strip(),
                roles=[role.strip() for role in (row.get("roles") or "").split(";")],
            )
            created.append(_create_user_with_invitation(
                db=db, organization_id=organization_id, department_id=department_id, request=request
            ))
        except Exception as exc:
            detail = exc.detail if isinstance(exc, user_service.UserServiceError) else "Invalid row"
            errors.append({"row": row_number, "email": row.get("email", ""), "message": detail})
    return {"created": created, "created_count": len(created), "errors": errors, "error_count": len(errors)}


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
    if get_settings().auth_provider == "supabase" and request.password:
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
