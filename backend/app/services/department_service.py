"""Tenant-scoped department administration and assignment validation."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.department import Department
from app.models.user import User
from app.services.audit_service import record_audit


class DepartmentNotFoundError(LookupError):
    """Raised when a department is outside the caller's organization."""


class DepartmentConflictError(ValueError):
    """Raised when a department change would break an active assignment."""


def _uuid(value: str | uuid.UUID, *, field_name: str) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise DepartmentNotFoundError(f"Invalid {field_name}") from exc


def _organization_id(value: str | uuid.UUID) -> uuid.UUID:
    return _uuid(value, field_name="organization id")


def _normalize_code(value: str) -> str:
    code = value.strip().upper().replace(" ", "_")
    if not code:
        raise DepartmentConflictError("Department code is required")
    return code


def _normalize_name(value: str) -> str:
    name = value.strip()
    if not name:
        raise DepartmentConflictError("Department name is required")
    return name


def _department(
    db: Session,
    department_id: str | uuid.UUID,
    organization_id: str | uuid.UUID,
    *,
    require_active: bool = False,
) -> Department:
    statement = select(Department).where(
        Department.id == _uuid(department_id, field_name="department id"),
        Department.organization_id == _organization_id(organization_id),
        Department.is_deleted.is_(False),
    )
    if require_active:
        statement = statement.where(Department.status == "active")
    department = db.scalar(statement)
    if department is None:
        detail = "Department must be active and belong to your organization" if require_active else "Department not found"
        raise DepartmentNotFoundError(detail)
    return department


def require_assignable_department(
    db: Session,
    department_id: str | uuid.UUID,
    organization_id: str | uuid.UUID,
) -> Department:
    """Return a live department that can receive an employee assignment."""

    return _department(db, department_id, organization_id, require_active=True)


def _ensure_code_available(
    db: Session,
    *,
    code: str,
    organization_id: uuid.UUID,
    excluding_id: uuid.UUID | None = None,
) -> None:
    statement = select(Department.id).where(
        Department.organization_id == organization_id,
        func.lower(Department.code) == code.lower(),
    )
    if excluding_id is not None:
        statement = statement.where(Department.id != excluding_id)
    if db.scalar(statement) is not None:
        raise DepartmentConflictError("A department with that code already exists")


def list_departments(
    db: Session,
    organization_id: str | uuid.UUID,
    *,
    include_inactive: bool = False,
) -> list[Department]:
    statement = select(Department).where(
        Department.organization_id == _organization_id(organization_id),
        Department.is_deleted.is_(False),
    )
    if not include_inactive:
        statement = statement.where(Department.status == "active")
    return list(db.scalars(statement.order_by(Department.name, Department.code, Department.id)).all())


def create_department(
    db: Session,
    *,
    organization_id: str | uuid.UUID,
    code: str,
    name: str,
    performed_by: str | None = None,
) -> Department:
    resolved_organization_id = _organization_id(organization_id)
    normalized_code = _normalize_code(code)
    normalized_name = _normalize_name(name)
    _ensure_code_available(db, code=normalized_code, organization_id=resolved_organization_id)
    department = Department(
        organization_id=resolved_organization_id,
        code=normalized_code,
        name=normalized_name,
        status="active",
    )
    db.add(department)
    db.flush()
    record_audit(
        db,
        "departments",
        str(department.id),
        "create",
        after={"code": department.code, "name": department.name, "status": department.status},
        performed_by=performed_by,
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DepartmentConflictError("A department with that code already exists") from exc
    db.refresh(department)
    return department


def update_department(
    db: Session,
    department_id: str | uuid.UUID,
    *,
    organization_id: str | uuid.UUID,
    performed_by: str | None = None,
    **changes: Any,
) -> Department:
    department = _department(db, department_id, organization_id)
    before = {"code": department.code, "name": department.name, "status": department.status}
    if "code" in changes and changes["code"] is not None:
        code = _normalize_code(str(changes["code"]))
        _ensure_code_available(
            db,
            code=code,
            organization_id=_organization_id(organization_id),
            excluding_id=department.id,
        )
        department.code = code
    if "name" in changes and changes["name"] is not None:
        department.name = _normalize_name(str(changes["name"]))
    if "status" in changes and changes["status"] is not None:
        status = str(changes["status"]).lower()
        if status not in {"active", "inactive"}:
            raise DepartmentConflictError("Department status must be active or inactive")
        if status == "inactive" and department.status != "inactive":
            active_member = db.scalar(
                select(User.id).where(
                    User.organization_id == department.organization_id,
                    User.department_id == department.id,
                    User.status == "active",
                    User.is_deleted.is_(False),
                )
            )
            if active_member is not None:
                raise DepartmentConflictError("Reassign active employees before deactivating this department")
        department.status = status
    record_audit(
        db,
        "departments",
        str(department.id),
        "update",
        before=before,
        after={"code": department.code, "name": department.name, "status": department.status},
        performed_by=performed_by,
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DepartmentConflictError("A department with that code already exists") from exc
    db.refresh(department)
    return department


def department_payload(department: Department) -> dict[str, object]:
    return {
        "id": str(department.id),
        "code": department.code,
        "name": department.name,
        "status": department.status,
        "department_head_user_id": str(department.department_head_user_id) if department.department_head_user_id else None,
    }
