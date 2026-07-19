"""Tenant-scoped department lookup for access-request administration."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_permission
from app.models.department import Department


router = APIRouter(prefix="/api/departments", tags=["departments"])


class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


@router.get("", response_model=list[DepartmentResponse])
def list_active_departments(
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("access_request:manage")),
) -> list[Department]:
    """List only departments that can safely be assigned to an access request."""

    organization_id = uuid.UUID(str(user["organization_id"]))
    return list(
        db.scalars(
            select(Department)
            .where(
                Department.organization_id == organization_id,
                Department.is_deleted.is_(False),
                Department.status == "active",
            )
            .order_by(Department.name, Department.code, Department.id)
        ).all()
    )
