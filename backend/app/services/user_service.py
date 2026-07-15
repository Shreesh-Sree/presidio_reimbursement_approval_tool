"""User administration and role-based access helpers.

This module deliberately owns the relationship-table writes instead of relying
on view-only ORM relationships.  That keeps role changes explicit, auditable,
and portable across SQLite tests and PostgreSQL deployments.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Iterable
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User
from app.models.user_role import UserRole


class UserServiceError(Exception):
    """A domain error that routes can safely expose as an HTTP response."""

    def __init__(self, detail: str, status_code: int = 400) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


# Keep permission definitions in one place so a brand-new deployment can be
# safely bootstrapped without hand-populating lookup tables.  New feature
# modules can extend this mapping without changing authorization mechanics.
SYSTEM_PERMISSIONS: dict[str, str] = {
    "user:create": "Create users",
    "user:read": "View users and organization hierarchy",
    "user:update": "Update users and reporting managers",
    "user:deactivate": "Deactivate users",
    "policy:manage": "Manage reimbursement policies",
    "category:manage": "Manage expense categories",
    "vendor:manage": "Manage vendors",
    "report:create": "Create and edit own expense reports",
    "report:read": "View accessible expense reports",
    "report:approve": "Approve, reject, or send back reports",
    "workflow:manage": "Manage approval workflow rules",
    "payment:manage": "Manage reimbursement payments",
    "notification:read": "Read notifications",
    "notification:manage": "Manage notification delivery",
    "comment:create": "Create report comments",
    "comment:read": "Read report comments",
}

SYSTEM_ROLES: dict[str, tuple[str, set[str]]] = {
    "administrator": ("Administrator", set(SYSTEM_PERMISSIONS)),
    "approver": (
        "Approver",
        {
            "report:create",
            "report:read",
            "report:approve",
            "notification:read",
            "comment:create",
            "comment:read",
        },
    ),
    "employee": (
        "Employee",
        {
            "report:create",
            "report:read",
            "notification:read",
            "comment:create",
            "comment:read",
        },
    ),
}


def ensure_system_roles_and_permissions(db: Session) -> None:
    """Create required lookup rows idempotently within the caller's transaction.

    The helper only flushes; callers decide when to commit.  This lets login,
    bootstrap, and protected requests use the same transaction boundary and
    prevents a partially populated RBAC catalog from being committed.
    """

    existing_permissions = {
        permission.code: permission
        for permission in db.scalars(select(Permission).where(Permission.is_deleted.is_(False))).all()
    }
    for code, description in SYSTEM_PERMISSIONS.items():
        permission = existing_permissions.get(code)
        if permission is None:
            module, action = code.split(":", 1)
            permission = Permission(
                code=code,
                module=module,
                action=action,
                description=description,
                is_active=True,
            )
            db.add(permission)
            existing_permissions[code] = permission
        else:
            permission.is_active = True
            permission.deleted_at = None
            permission.is_deleted = False
    db.flush()

    existing_roles = {
        role.code: role
        for role in db.scalars(select(Role).where(Role.is_deleted.is_(False))).all()
    }
    for code, (name, _) in SYSTEM_ROLES.items():
        role = existing_roles.get(code)
        if role is None:
            role = Role(code=code, name=name, is_system_role=True, is_active=True)
            db.add(role)
            existing_roles[code] = role
        else:
            role.name = name
            role.is_system_role = True
            role.is_active = True
            role.deleted_at = None
            role.is_deleted = False
    db.flush()

    existing_links = {
        (link.role_id, link.permission_id): link
        for link in db.scalars(select(RolePermission)).all()
    }
    for role_code, (_, permission_codes) in SYSTEM_ROLES.items():
        role = existing_roles[role_code]
        for permission_code in permission_codes:
            permission = existing_permissions[permission_code]
            key = (role.id, permission.id)
            link = existing_links.get(key)
            if link is None:
                db.add(RolePermission(role_id=role.id, permission_id=permission.id))
            else:
                link.is_deleted = False
                link.deleted_at = None
    db.flush()


def role_codes_for_user(db: Session, user_id: uuid.UUID) -> list[str]:
    statement = (
        select(Role.code)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(
            UserRole.user_id == user_id,
            UserRole.is_deleted.is_(False),
            Role.is_deleted.is_(False),
            Role.is_active.is_(True),
        )
        .order_by(Role.code)
    )
    return list(db.scalars(statement).all())


def permission_codes_for_user(db: Session, user_id: uuid.UUID) -> list[str]:
    statement = (
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .join(Role, Role.id == UserRole.role_id)
        .where(
            UserRole.user_id == user_id,
            UserRole.is_deleted.is_(False),
            RolePermission.is_deleted.is_(False),
            Role.is_deleted.is_(False),
            Role.is_active.is_(True),
            Permission.is_deleted.is_(False),
            Permission.is_active.is_(True),
        )
        .distinct()
        .order_by(Permission.code)
    )
    return list(db.scalars(statement).all())


def list_roles(db: Session) -> list[dict[str, str]]:
    ensure_system_roles_and_permissions(db)
    roles = db.scalars(
        select(Role)
        .where(Role.is_deleted.is_(False), Role.is_active.is_(True))
        .order_by(Role.name)
    ).all()
    return [{"code": role.code, "name": role.name} for role in roles]


def _active_role_records(db: Session, role_codes: Iterable[str]) -> list[Role]:
    codes = sorted({code.strip().lower() for code in role_codes if code.strip()})
    if not codes:
        raise UserServiceError("at least one role is required")

    roles = db.scalars(
        select(Role).where(
            Role.code.in_(codes),
            Role.is_deleted.is_(False),
            Role.is_active.is_(True),
        )
    ).all()
    found_codes = {role.code for role in roles}
    missing = sorted(set(codes) - found_codes)
    if missing:
        raise UserServiceError(f"Unknown or inactive role: {', '.join(missing)}")
    return roles


def _has_role(db: Session, user_id: uuid.UUID, role_code: str) -> bool:
    return role_code in role_codes_for_user(db, user_id)


def _email_exists(db: Session, organization_id: uuid.UUID, email: str, exclude_user_id: uuid.UUID | None = None) -> bool:
    statement = select(User.id).where(
        User.organization_id == organization_id,
        func.lower(User.email) == email.lower(),
        User.is_deleted.is_(False),
    )
    if exclude_user_id is not None:
        statement = statement.where(User.id != exclude_user_id)
    return db.scalar(statement) is not None


def _username_for_email(db: Session, organization_id: uuid.UUID, email: str, exclude_user_id: uuid.UUID | None = None) -> str:
    local_part = email.split("@", 1)[0].lower()
    base = re.sub(r"[^a-z0-9]+", ".", local_part).strip(".") or "user"
    base = base[:90]
    candidate = base
    suffix = 1
    while True:
        statement = select(User.id).where(
            User.organization_id == organization_id,
            User.username == candidate,
            User.is_deleted.is_(False),
        )
        if exclude_user_id is not None:
            statement = statement.where(User.id != exclude_user_id)
        if db.scalar(statement) is None:
            return candidate
        suffix += 1
        candidate = f"{base[:96]}-{suffix}"


def _employee_number(db: Session, organization_id: uuid.UUID) -> str:
    while True:
        candidate = f"EMP-{uuid.uuid4().hex[:12].upper()}"
        exists = db.scalar(
            select(User.id).where(
                User.organization_id == organization_id,
                User.employee_number == candidate,
                User.is_deleted.is_(False),
            )
        )
        if exists is None:
            return candidate


def _get_scoped_user(db: Session, user_id: uuid.UUID, organization_id: uuid.UUID) -> User:
    user = db.scalar(
        select(User).where(
            User.id == user_id,
            User.organization_id == organization_id,
            User.is_deleted.is_(False),
        )
    )
    if user is None:
        raise UserServiceError("User not found", 404)
    return user


def _validate_manager(
    db: Session,
    organization_id: uuid.UUID,
    manager_id: uuid.UUID | None,
    target_user_id: uuid.UUID | None = None,
) -> None:
    if manager_id is None:
        return
    if target_user_id is not None and manager_id == target_user_id:
        raise UserServiceError("A user cannot report to themselves")

    manager = _get_scoped_user(db, manager_id, organization_id)
    if manager.status != "active":
        raise UserServiceError("Reporting manager must be active")
    if not _has_role(db, manager.id, "approver"):
        raise UserServiceError("Reporting manager must have the approver role")

    # Walk upward and reject both a direct self-reference and an existing
    # malformed cycle; this prevents an update from making the tree recursive.
    visited: set[uuid.UUID] = set()
    ancestor: User | None = manager
    while ancestor is not None:
        if ancestor.id in visited:
            raise UserServiceError("Reporting manager hierarchy contains a cycle")
        visited.add(ancestor.id)
        if target_user_id is not None and ancestor.id == target_user_id:
            raise UserServiceError("Reporting manager would create a cycle")
        if ancestor.manager_user_id is None:
            break
        ancestor = db.scalar(
            select(User).where(
                User.id == ancestor.manager_user_id,
                User.organization_id == organization_id,
                User.is_deleted.is_(False),
            )
        )


def _replace_roles(db: Session, user: User, role_codes: Iterable[str]) -> None:
    roles = _active_role_records(db, role_codes)
    now = datetime.now(UTC)
    existing_links = db.scalars(
        select(UserRole).where(UserRole.user_id == user.id)
    ).all()
    links_by_role = {link.role_id: link for link in existing_links}
    desired_role_ids = {role.id for role in roles}
    for link in existing_links:
        if link.role_id not in desired_role_ids:
            link.is_deleted = True
            link.deleted_at = now
    for role in roles:
        link = links_by_role.get(role.id)
        if link is None:
            db.add(UserRole(user_id=user.id, role_id=role.id))
        else:
            link.is_deleted = False
            link.deleted_at = None
    db.flush()


def _active_administrator_count(db: Session, organization_id: uuid.UUID) -> int:
    statement = (
        select(func.count(User.id))
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(
            User.organization_id == organization_id,
            User.status == "active",
            User.is_deleted.is_(False),
            UserRole.is_deleted.is_(False),
            Role.code == "administrator",
            Role.is_deleted.is_(False),
            Role.is_active.is_(True),
        )
    )
    return int(db.scalar(statement) or 0)


def _assert_not_removing_last_administrator(
    db: Session,
    user: User,
    new_role_codes: Iterable[str],
) -> None:
    if _has_role(db, user.id, "administrator") and "administrator" not in set(new_role_codes):
        if _active_administrator_count(db, user.organization_id) <= 1:
            raise UserServiceError("At least one active administrator is required")


def user_response(db: Session, user: User) -> dict[str, object]:
    manager = user.manager
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "status": user.status,
        "roles": role_codes_for_user(db, user.id),
        "manager_id": str(user.manager_user_id) if user.manager_user_id else None,
        "manager_name": manager.full_name if manager and not manager.is_deleted else None,
    }


def create_user(
    db: Session,
    *,
    organization_id: uuid.UUID,
    department_id: uuid.UUID,
    email: str,
    password: str,
    full_name: str,
    role_codes: Iterable[str],
    manager_id: uuid.UUID | None,
) -> dict[str, object]:
    ensure_system_roles_and_permissions(db)
    normalized_email = email.lower()
    if _email_exists(db, organization_id, normalized_email):
        raise UserServiceError("A user with that email already exists", 409)
    _validate_manager(db, organization_id, manager_id)

    user = User(
        organization_id=organization_id,
        department_id=department_id,
        manager_user_id=manager_id,
        employee_number=_employee_number(db, organization_id),
        username=_username_for_email(db, organization_id, normalized_email),
        email=normalized_email,
        password_hash=hash_password(password),
        full_name=full_name.strip(),
        status="active",
    )
    db.add(user)
    db.flush()
    _replace_roles(db, user, role_codes)
    db.commit()
    db.refresh(user)
    return user_response(db, user)


def list_users(db: Session, organization_id: uuid.UUID) -> list[dict[str, object]]:
    users = db.scalars(
        select(User)
        .where(User.organization_id == organization_id, User.is_deleted.is_(False))
        .order_by(User.full_name, User.email)
    ).all()
    return [user_response(db, user) for user in users]


def get_user(db: Session, user_id: uuid.UUID, organization_id: uuid.UUID) -> dict[str, object]:
    return user_response(db, _get_scoped_user(db, user_id, organization_id))


def update_user(
    db: Session,
    *,
    user_id: uuid.UUID,
    organization_id: uuid.UUID,
    changes: dict[str, object],
) -> dict[str, object]:
    user = _get_scoped_user(db, user_id, organization_id)

    if "email" in changes and changes["email"] is not None:
        email = str(changes["email"]).lower()
        if _email_exists(db, organization_id, email, exclude_user_id=user.id):
            raise UserServiceError("A user with that email already exists", 409)
        user.email = email
        user.username = _username_for_email(db, organization_id, email, exclude_user_id=user.id)
    if "full_name" in changes and changes["full_name"] is not None:
        user.full_name = str(changes["full_name"]).strip()
    if "password" in changes and changes["password"]:
        user.password_hash = hash_password(str(changes["password"]))
    if "roles" in changes and changes["roles"] is not None:
        role_codes = list(changes["roles"])  # Pydantic already validates the list shape.
        _assert_not_removing_last_administrator(db, user, role_codes)
        _replace_roles(db, user, role_codes)
    if "manager_id" in changes:
        manager_id = changes["manager_id"]
        if manager_id is not None and not isinstance(manager_id, uuid.UUID):
            manager_id = uuid.UUID(str(manager_id))
        _validate_manager(db, organization_id, manager_id, user.id)
        user.manager_user_id = manager_id

    db.commit()
    db.refresh(user)
    return user_response(db, user)


def deactivate_user(
    db: Session,
    *,
    user_id: uuid.UUID,
    organization_id: uuid.UUID,
    actor_user_id: uuid.UUID,
) -> dict[str, object]:
    user = _get_scoped_user(db, user_id, organization_id)
    if user.id == actor_user_id:
        raise UserServiceError("You cannot deactivate your own account")
    if user.status != "active":
        return user_response(db, user)
    if _has_role(db, user.id, "administrator") and _active_administrator_count(db, organization_id) <= 1:
        raise UserServiceError("At least one active administrator is required")

    has_active_reports = db.scalar(
        select(User.id).where(
            User.organization_id == organization_id,
            User.manager_user_id == user.id,
            User.status == "active",
            User.is_deleted.is_(False),
        )
    )
    if has_active_reports is not None:
        raise UserServiceError("Reassign direct reports before deactivating this user", 409)

    user.status = "inactive"
    db.commit()
    db.refresh(user)
    return user_response(db, user)
