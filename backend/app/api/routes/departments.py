"""Tenant-scoped department administration and lookup endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_permission
from app.services import department_service


router = APIRouter(prefix="/api/departments", tags=["departments"])


class DepartmentResponse(BaseModel):
    id: str
    code: str
    name: str
    status: str
    department_head_user_id: str | None = None


class DepartmentCreateInput(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)


class DepartmentUpdateInput(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    status: str | None = Field(default=None, pattern="^(active|inactive)$")


def _department_error(exc: Exception) -> None:
    if isinstance(exc, department_service.DepartmentNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, department_service.DepartmentConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    raise exc


@router.get("", response_model=list[DepartmentResponse])
def list_departments(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("user:read")),
) -> list[dict[str, object]]:
    """List active departments by default; admins can include inactive records."""

    return [
        department_service.department_payload(department)
        for department in department_service.list_departments(
            db,
            user["organization_id"],
            include_inactive=include_inactive,
        )
    ]


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
def create_department(
    payload: DepartmentCreateInput,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("user:update")),
) -> dict[str, object]:
    try:
        return department_service.department_payload(
            department_service.create_department(
                db,
                organization_id=user["organization_id"],
                performed_by=str(user["user_id"]),
                **payload.model_dump(),
            )
        )
    except Exception as exc:
        _department_error(exc)


@router.patch("/{department_id}", response_model=DepartmentResponse)
def update_department(
    department_id: str,
    payload: DepartmentUpdateInput,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("user:update")),
) -> dict[str, object]:
    try:
        changes: dict[str, Any] = payload.model_dump(exclude_unset=True)
        return department_service.department_payload(
            department_service.update_department(
                db,
                department_id,
                organization_id=user["organization_id"],
                performed_by=str(user["user_id"]),
                **changes,
            )
        )
    except Exception as exc:
        _department_error(exc)
