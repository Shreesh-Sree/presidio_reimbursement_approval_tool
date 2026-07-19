"""Administrator-managed approval-routing rule operations.

The approval engine deliberately owns how a saved rule is evaluated at
submission time.  This service owns the other side of that contract: scoped,
validated CRUD for the people and thresholds an administrator may configure.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.department import Department
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User
from app.models.workflow_rule import WorkflowRule
from app.services.audit_service import record_audit
from app.services.user_service import permission_codes_for_user


class WorkflowRuleError(Exception):
    """A domain error that is safe to return from the workflow API."""


class WorkflowRuleNotFoundError(WorkflowRuleError):
    pass


class WorkflowRuleConflictError(WorkflowRuleError):
    pass


class WorkflowRuleValidationError(WorkflowRuleError):
    pass


_CONDITION_KEYS = {"min_total", "max_total", "department_id", "currency_code"}
_MAX_APPROVAL_STEPS = 10
_ROLE_CODE = re.compile(r"^[a-z][a-z0-9_-]{0,99}$")
_CURRENCY_CODE = re.compile(r"^[A-Z]{3,10}$")


def _as_uuid(value: uuid.UUID | str, *, field_name: str) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise WorkflowRuleValidationError(f"Invalid {field_name}") from exc


def _money(value: object, *, field_name: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise WorkflowRuleValidationError(f"{field_name} must be a valid amount") from exc
    if not parsed.is_finite() or parsed < 0:
        raise WorkflowRuleValidationError(f"{field_name} must be zero or greater")
    return parsed.quantize(Decimal("0.01"))


def _belongs_to_organization(rule: WorkflowRule, organization_id: uuid.UUID) -> bool:
    """Return whether a rule belongs to the requested tenant.

    Organization ownership used to live in ``conditions_json``.  The model
    now carries it as a non-null foreign key, so this helper deliberately does
    not fall back to the legacy JSON predicate.
    """

    return rule.organization_id == organization_id


def _active_scoped_rule(
    db: Session,
    rule_id: uuid.UUID | str,
    organization_id: uuid.UUID,
) -> WorkflowRule:
    resolved_id = _as_uuid(rule_id, field_name="workflow rule id")
    rule = db.scalar(
        select(WorkflowRule).where(
            WorkflowRule.id == resolved_id,
            WorkflowRule.organization_id == organization_id,
            WorkflowRule.is_deleted.is_(False),
        )
    )
    if rule is None:
        raise WorkflowRuleNotFoundError("Workflow rule not found")
    return rule


def _ensure_name_available(
    db: Session,
    name: str,
    *,
    organization_id: uuid.UUID,
    excluding_id: uuid.UUID | None = None,
) -> None:
    statement = select(WorkflowRule.id).where(
        WorkflowRule.organization_id == organization_id,
        func.lower(WorkflowRule.name) == name.lower(),
        WorkflowRule.is_deleted.is_(False),
    )
    if excluding_id is not None:
        statement = statement.where(WorkflowRule.id != excluding_id)
    if db.scalar(statement) is not None:
        raise WorkflowRuleConflictError("A workflow rule with that name already exists")


def _normalize_conditions(
    db: Session,
    raw_conditions: Mapping[str, Any] | None,
    organization_id: uuid.UUID,
) -> dict[str, str]:
    conditions = dict(raw_conditions or {})
    unexpected = set(conditions) - _CONDITION_KEYS
    if unexpected:
        raise WorkflowRuleValidationError("Unsupported workflow condition")

    normalized: dict[str, str] = {}
    min_total = conditions.get("min_total")
    max_total = conditions.get("max_total")
    if min_total is not None:
        normalized["min_total"] = str(_money(min_total, field_name="Minimum total"))
    if max_total is not None:
        normalized["max_total"] = str(_money(max_total, field_name="Maximum total"))
    if min_total is not None and max_total is not None:
        if Decimal(normalized["min_total"]) > Decimal(normalized["max_total"]):
            raise WorkflowRuleValidationError("Minimum total cannot exceed maximum total")

    department_value = conditions.get("department_id")
    if department_value is not None:
        department_id = _as_uuid(department_value, field_name="department id")
        department = db.scalar(
            select(Department).where(
                Department.id == department_id,
                Department.organization_id == organization_id,
                Department.is_deleted.is_(False),
                Department.status == "active",
            )
        )
        if department is None:
            raise WorkflowRuleValidationError("Department must be active and belong to your organization")
        normalized["department_id"] = str(department.id)

    currency_value = conditions.get("currency_code")
    if currency_value is not None:
        currency_code = str(currency_value).strip().upper()
        if not _CURRENCY_CODE.fullmatch(currency_code):
            raise WorkflowRuleValidationError("Currency code must contain 3 to 10 letters")
        normalized["currency_code"] = currency_code
    return normalized


def _ensure_explicit_approver(db: Session, user_id: uuid.UUID, organization_id: uuid.UUID) -> None:
    user = db.scalar(
        select(User).where(
            User.id == user_id,
            User.organization_id == organization_id,
            User.is_deleted.is_(False),
            User.status == "active",
        )
    )
    if user is None:
        raise WorkflowRuleValidationError("Configured approver must be active and belong to your organization")
    if "report:approve" not in set(permission_codes_for_user(db, user.id)):
        raise WorkflowRuleValidationError("Configured user must have report approval permission")


def _ensure_approver_role(db: Session, role_code: str) -> None:
    role = db.scalar(
        select(Role)
        .join(RolePermission, RolePermission.role_id == Role.id)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .where(
            Role.code == role_code,
            Role.is_deleted.is_(False),
            Role.is_active.is_(True),
            RolePermission.is_deleted.is_(False),
            Permission.code == "report:approve",
            Permission.is_deleted.is_(False),
            Permission.is_active.is_(True),
        )
    )
    if role is None:
        raise WorkflowRuleValidationError("Configured role must be active and able to approve reports")


def _normalize_chain(
    db: Session,
    raw_chain: Sequence[Mapping[str, Any]],
    organization_id: uuid.UUID,
) -> list[dict[str, int | str]]:
    if not raw_chain or len(raw_chain) > _MAX_APPROVAL_STEPS:
        raise WorkflowRuleValidationError(
            f"Approval chain must include between 1 and {_MAX_APPROVAL_STEPS} steps"
        )

    normalized: list[dict[str, int | str]] = []
    seen_steps: set[tuple[str, str]] = set()
    for index, raw_step in enumerate(raw_chain, start=1):
        if not isinstance(raw_step, Mapping):
            raise WorkflowRuleValidationError(f"Approval step {index} is invalid")
        selectors = [
            raw_step.get("manager_level") is not None,
            raw_step.get("user_id") is not None,
            raw_step.get("role_code") is not None,
        ]
        if sum(selectors) != 1:
            raise WorkflowRuleValidationError(
                f"Approval step {index} must choose exactly one of manager level, user, or role"
            )
        if selectors[0]:
            manager_level = raw_step["manager_level"]
            if isinstance(manager_level, bool) or not isinstance(manager_level, int):
                raise WorkflowRuleValidationError(f"Approval step {index} manager level must be a whole number")
            if not 1 <= manager_level <= _MAX_APPROVAL_STEPS:
                raise WorkflowRuleValidationError(
                    f"Approval step {index} manager level must be between 1 and {_MAX_APPROVAL_STEPS}"
                )
            key = ("manager_level", str(manager_level))
            step: dict[str, int | str] = {"manager_level": manager_level}
        elif selectors[1]:
            user_id = _as_uuid(raw_step["user_id"], field_name=f"approval step {index} user id")
            _ensure_explicit_approver(db, user_id, organization_id)
            key = ("user_id", str(user_id))
            step = {"user_id": str(user_id)}
        else:
            role_code = str(raw_step["role_code"]).strip().lower()
            if not _ROLE_CODE.fullmatch(role_code):
                raise WorkflowRuleValidationError(f"Approval step {index} role is invalid")
            _ensure_approver_role(db, role_code)
            key = ("role_code", role_code)
            step = {"role_code": role_code}
        if key in seen_steps:
            raise WorkflowRuleValidationError("Approval chain cannot contain duplicate steps")
        seen_steps.add(key)
        normalized.append(step)
    return normalized


def _public_conditions(conditions: Mapping[str, Any] | None) -> dict[str, Any]:
    public = {key: value for key, value in dict(conditions or {}).items() if key != "organization_id"}
    for key in ("min_total", "max_total"):
        if key in public:
            public[key] = float(Decimal(str(public[key])))
    return public


def workflow_rule_payload(rule: WorkflowRule) -> dict[str, Any]:
    return {
        "id": str(rule.id),
        "name": rule.name,
        "conditions": _public_conditions(rule.conditions_json),
        "approval_chain": list(rule.approval_chain_json or []),
        "priority": rule.priority,
        "is_active": rule.is_active,
        "is_deleted": rule.is_deleted,
        "created_at": rule.created_at.isoformat() if rule.created_at else None,
        "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
    }


def list_workflow_rules(db: Session, organization_id: uuid.UUID | str, *, include_archived: bool = False) -> list[WorkflowRule]:
    organization = _as_uuid(organization_id, field_name="organization id")
    statement = select(WorkflowRule).where(WorkflowRule.organization_id == organization)
    if not include_archived:
        statement = statement.where(WorkflowRule.is_deleted.is_(False))
    return list(db.scalars(statement.order_by(WorkflowRule.priority.asc(), WorkflowRule.created_at.asc())))


def get_workflow_rule(
    db: Session,
    rule_id: uuid.UUID | str,
    organization_id: uuid.UUID | str,
) -> WorkflowRule:
    organization = _as_uuid(organization_id, field_name="organization id")
    return _active_scoped_rule(db, rule_id, organization)


def create_workflow_rule(
    db: Session,
    *,
    organization_id: uuid.UUID | str,
    actor_user_id: uuid.UUID | str,
    name: str,
    conditions: Mapping[str, Any] | None,
    approval_chain: Sequence[Mapping[str, Any]],
    priority: int = 100,
    is_active: bool = True,
) -> WorkflowRule:
    organization = _as_uuid(organization_id, field_name="organization id")
    normalized_name = name.strip()
    if not normalized_name:
        raise WorkflowRuleValidationError("Workflow rule name is required")
    _ensure_name_available(db, normalized_name, organization_id=organization)
    normalized_conditions = _normalize_conditions(db, conditions, organization)
    normalized_chain = _normalize_chain(db, approval_chain, organization)
    rule = WorkflowRule(
        organization_id=organization,
        name=normalized_name,
        conditions_json=normalized_conditions,
        approval_chain_json=normalized_chain,
        priority=int(priority),
        is_active=bool(is_active),
    )
    db.add(rule)
    db.flush()
    record_audit(
        db,
        "workflow_rules",
        str(rule.id),
        "created",
        after=workflow_rule_payload(rule),
        performed_by=str(actor_user_id),
    )
    db.commit()
    db.refresh(rule)
    return rule


def update_workflow_rule(
    db: Session,
    rule_id: uuid.UUID | str,
    *,
    organization_id: uuid.UUID | str,
    actor_user_id: uuid.UUID | str,
    changes: Mapping[str, Any],
) -> WorkflowRule:
    organization = _as_uuid(organization_id, field_name="organization id")
    rule = _active_scoped_rule(db, rule_id, organization)
    before = workflow_rule_payload(rule)
    allowed = {"name", "conditions", "approval_chain", "priority", "is_active"}
    unexpected = set(changes) - allowed
    if unexpected:
        raise WorkflowRuleValidationError("Unsupported workflow rule field")
    if not changes:
        raise WorkflowRuleValidationError("Provide at least one workflow rule field to update")
    if "name" in changes:
        name = str(changes["name"] or "").strip()
        if not name:
            raise WorkflowRuleValidationError("Workflow rule name is required")
        _ensure_name_available(db, name, organization_id=organization, excluding_id=rule.id)
        rule.name = name
    if "conditions" in changes:
        rule.conditions_json = _normalize_conditions(db, changes["conditions"], organization)
    if "approval_chain" in changes:
        chain = changes["approval_chain"]
        if not isinstance(chain, Sequence) or isinstance(chain, (str, bytes)):
            raise WorkflowRuleValidationError("Approval chain is invalid")
        rule.approval_chain_json = _normalize_chain(db, chain, organization)
    if "priority" in changes:
        priority = changes["priority"]
        if isinstance(priority, bool) or not isinstance(priority, int) or priority < 0:
            raise WorkflowRuleValidationError("Priority must be a non-negative whole number")
        rule.priority = priority
    if "is_active" in changes:
        rule.is_active = bool(changes["is_active"])
    db.flush()
    record_audit(
        db,
        "workflow_rules",
        str(rule.id),
        "updated",
        before=before,
        after=workflow_rule_payload(rule),
        performed_by=str(actor_user_id),
    )
    db.commit()
    db.refresh(rule)
    return rule


def delete_workflow_rule(
    db: Session,
    rule_id: uuid.UUID | str,
    *,
    organization_id: uuid.UUID | str,
    actor_user_id: uuid.UUID | str,
) -> None:
    organization = _as_uuid(organization_id, field_name="organization id")
    rule = _active_scoped_rule(db, rule_id, organization)
    before = workflow_rule_payload(rule)
    rule.is_deleted = True
    rule.deleted_at = datetime.now(UTC)
    db.flush()
    record_audit(
        db,
        "workflow_rules",
        str(rule.id),
        "deleted",
        before=before,
        performed_by=str(actor_user_id),
    )
    db.commit()


def restore_workflow_rule(db: Session, rule_id: uuid.UUID | str, *, organization_id: uuid.UUID | str) -> WorkflowRule:
    organization = _as_uuid(organization_id, field_name="organization id")
    rule = db.scalar(
        select(WorkflowRule).where(
            WorkflowRule.id == _as_uuid(rule_id, field_name="workflow rule id"),
            WorkflowRule.organization_id == organization,
        )
    )
    if rule is None:
        raise WorkflowRuleNotFoundError("Workflow rule not found")
    rule.is_deleted = False
    rule.deleted_at = None
    db.commit(); db.refresh(rule)
    return rule
