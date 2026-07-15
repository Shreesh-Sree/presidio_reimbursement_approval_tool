"""Versioned reimbursement policy management.

Policy rules remain structured rows, rather than an opaque uploaded document, so
the same version can be evaluated at submission time and retained by reports as
their applied-policy snapshot.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Any, Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.expense_category import ExpenseCategory
from app.models.policy import Policy, PolicyRule
from app.models.vendor import Vendor
from app.services.audit_service import record_audit
from app.services import storage_service
from app.services.vendor_service import normalize_vendor_name


class PolicyNotFoundError(LookupError):
    pass


class PolicyConflictError(ValueError):
    pass


_UNSET = object()


def _uuid(value: str | uuid.UUID | None, *, field_name: str) -> uuid.UUID | None:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except ValueError as exc:
        raise PolicyConflictError(f"Invalid {field_name}") from exc


def _organization_id(value: str | uuid.UUID | None) -> uuid.UUID:
    organization_id = _uuid(value, field_name="organization id")
    if organization_id is None:
        raise PolicyConflictError("organization id is required")
    return organization_id


def _as_datetime(value: datetime | date | str | None, *, field_name: str, required: bool = False) -> datetime | None:
    if value is None:
        if required:
            raise PolicyConflictError(f"{field_name} is required")
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(value, time.min)
    else:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (TypeError, ValueError) as exc:
            raise PolicyConflictError(f"{field_name} must be an ISO-8601 date or datetime") from exc
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _as_rule_dict(rule: Any) -> dict[str, Any]:
    if hasattr(rule, "model_dump"):
        return rule.model_dump(exclude_unset=True)
    if isinstance(rule, dict):
        return rule
    raise PolicyConflictError("Each policy rule must be an object")


def _rule_number(rule: dict[str, Any], key: str) -> Decimal | None:
    value = rule.get(key)
    if value is None or value == "":
        return None
    try:
        number = Decimal(str(value))
    except Exception as exc:
        raise PolicyConflictError(f"{key} must be a number") from exc
    if number < 0:
        raise PolicyConflictError(f"{key} cannot be negative")
    return number


def _active_policy(
    db: Session,
    policy_id: str | uuid.UUID,
    organization_id: str | uuid.UUID,
) -> Policy:
    resolved_id = _uuid(policy_id, field_name="policy id")
    resolved_organization_id = _organization_id(organization_id)
    policy = db.scalar(
        select(Policy)
        .options(selectinload(Policy.rules))
        .where(
            Policy.id == resolved_id,
            Policy.organization_id == resolved_organization_id,
            Policy.is_deleted.is_(False),
        )
    )
    if policy is None:
        raise PolicyNotFoundError("Policy not found")
    return policy


def _category_code(name: str) -> str:
    code = re.sub(r"[^A-Z0-9]+", "-", name.upper()).strip("-")
    return (code or "CATEGORY")[:90]


def _resolve_category(db: Session, category_id: Any, category_name: Any) -> uuid.UUID | None:
    resolved_id = _uuid(category_id, field_name="category id")
    if resolved_id is not None:
        category = db.scalar(
            select(ExpenseCategory).where(
                ExpenseCategory.id == resolved_id,
                ExpenseCategory.is_deleted.is_(False),
            )
        )
        if category is None:
            raise PolicyConflictError("Policy rule refers to a missing category")
        return category.id
    if not category_name or not str(category_name).strip():
        return None
    name = str(category_name).strip()
    category = db.scalar(
        select(ExpenseCategory).where(
            func.lower(ExpenseCategory.name) == name.lower(),
            ExpenseCategory.is_deleted.is_(False),
        )
    )
    if category is not None:
        return category.id

    # The UI permits entering category names while defining a new policy.  Make
    # that workflow useful by creating a top-level category in the same
    # transaction, while keeping codes globally unique.
    base_code = _category_code(name)
    candidate = base_code
    suffix = 2
    while db.scalar(select(ExpenseCategory.id).where(ExpenseCategory.code == candidate)) is not None:
        candidate = f"{base_code[:84]}-{suffix}"
        suffix += 1
    category = ExpenseCategory(code=candidate, name=name, receipt_required=True)
    db.add(category)
    db.flush()
    return category.id


def _resolve_vendor(db: Session, vendor_id: Any, vendor_name: Any) -> uuid.UUID | None:
    resolved_id = _uuid(vendor_id, field_name="vendor id")
    if resolved_id is not None:
        vendor = db.scalar(
            select(Vendor).where(Vendor.id == resolved_id, Vendor.is_deleted.is_(False))
        )
        if vendor is None:
            raise PolicyConflictError("Policy rule refers to a missing vendor")
        return vendor.id
    if not vendor_name or not str(vendor_name).strip():
        return None
    name = str(vendor_name).strip()
    normalized_name = normalize_vendor_name(name)
    vendor = db.scalar(
        select(Vendor).where(
            func.lower(Vendor.normalized_name) == normalized_name,
            Vendor.is_deleted.is_(False),
        )
    )
    if vendor is not None:
        return vendor.id
    vendor = Vendor(name=name, normalized_name=normalized_name)
    db.add(vendor)
    db.flush()
    return vendor.id


def _replace_rules(db: Session, policy: Policy, rules_data: Iterable[Any]) -> None:
    for existing_rule in list(policy.rules):
        db.delete(existing_rule)
    db.flush()

    for raw_rule in rules_data:
        rule = _as_rule_dict(raw_rule)
        category_id = _resolve_category(db, rule.get("category_id"), rule.get("category_name"))
        vendor_id = _resolve_vendor(db, rule.get("vendor_id"), rule.get("vendor_name"))
        caps = {
            field: _rule_number(rule, field)
            for field in ("max_per_day", "max_per_trip", "per_category_cap", "receipt_required_above")
        }
        if category_id is None and vendor_id is None and not any(value is not None for value in caps.values()):
            raise PolicyConflictError("A policy rule must define a scope or at least one constraint")
        db.add(
            PolicyRule(
                policy_id=policy.id,
                category_id=category_id,
                vendor_id=vendor_id,
                **caps,
            )
        )
    db.flush()


def create_policy_version(
    db: Session,
    name: str,
    version_label: str,
    effective_from: datetime | date | str,
    *,
    organization_id: str | uuid.UUID,
    effective_to: datetime | date | str | None = None,
    rules_data: Iterable[Any] | dict[str, Any] | None = None,
) -> Policy:
    resolved_organization_id = _organization_id(organization_id)
    cleaned_name = name.strip()
    cleaned_version = version_label.strip()
    if not cleaned_name or not cleaned_version:
        raise PolicyConflictError("Policy name and version label are required")
    if db.scalar(
        select(Policy.id).where(
            Policy.organization_id == resolved_organization_id,
            func.lower(Policy.name) == cleaned_name.lower(),
            func.lower(Policy.version_label) == cleaned_version.lower(),
            Policy.is_deleted.is_(False),
        )
    ) is not None:
        raise PolicyConflictError("A policy version with this name and label already exists")

    starts_at = _as_datetime(effective_from, field_name="effective_from", required=True)
    ends_at = _as_datetime(effective_to, field_name="effective_to")
    if ends_at is not None and ends_at < starts_at:
        raise PolicyConflictError("effective_to cannot be before effective_from")
    policy = Policy(
        organization_id=resolved_organization_id,
        name=cleaned_name,
        version_label=cleaned_version,
        is_active=False,
        effective_from=starts_at,
        effective_to=ends_at,
    )
    db.add(policy)
    db.flush()
    supplied_rules = rules_data.get("rules", []) if isinstance(rules_data, dict) else (rules_data or [])
    _replace_rules(db, policy, supplied_rules)
    record_audit(
        db,
        "policies",
        str(policy.id),
        "create",
        after={
            "organization_id": str(policy.organization_id),
            "name": policy.name,
            "version_label": policy.version_label,
            "is_active": policy.is_active,
        },
    )
    db.commit()
    return _active_policy(db, policy.id, resolved_organization_id)


def update_policy_version(
    db: Session,
    policy_id: str | uuid.UUID,
    *,
    organization_id: str | uuid.UUID,
    name: str | None = None,
    version_label: str | None = None,
    effective_from: datetime | date | str | None = None,
    effective_to: datetime | date | str | None | object = _UNSET,
    rules_data: Iterable[Any] | None = None,
) -> Policy:
    resolved_organization_id = _organization_id(organization_id)
    policy = _active_policy(db, policy_id, resolved_organization_id)
    before = {
        "name": policy.name,
        "version_label": policy.version_label,
        "effective_from": str(policy.effective_from),
        "effective_to": str(policy.effective_to) if policy.effective_to else None,
    }
    if policy.is_active:
        raise PolicyConflictError("Active policy versions are immutable; create a new version for future claims")
    if name is not None:
        policy.name = name.strip()
    if version_label is not None:
        policy.version_label = version_label.strip()
    if not policy.name or not policy.version_label:
        raise PolicyConflictError("Policy name and version label are required")
    duplicate = db.scalar(
        select(Policy.id).where(
            Policy.organization_id == resolved_organization_id,
            func.lower(Policy.name) == policy.name.lower(),
            func.lower(Policy.version_label) == policy.version_label.lower(),
            Policy.id != policy.id,
            Policy.is_deleted.is_(False),
        )
    )
    if duplicate is not None:
        raise PolicyConflictError("A policy version with this name and label already exists")
    if effective_from is not None:
        policy.effective_from = _as_datetime(effective_from, field_name="effective_from", required=True)
    if effective_to is not _UNSET:
        policy.effective_to = _as_datetime(effective_to, field_name="effective_to")
    if policy.effective_to is not None and policy.effective_to < policy.effective_from:
        raise PolicyConflictError("effective_to cannot be before effective_from")
    if rules_data is not None:
        _replace_rules(db, policy, rules_data)
    record_audit(
        db,
        "policies",
        str(policy.id),
        "update",
        before=before,
        after={
            "name": policy.name,
            "version_label": policy.version_label,
            "effective_from": str(policy.effective_from),
            "effective_to": str(policy.effective_to) if policy.effective_to else None,
        },
    )
    db.commit()
    return _active_policy(db, policy.id, resolved_organization_id)


def activate_policy(
    db: Session,
    policy_id: str | uuid.UUID,
    *,
    organization_id: str | uuid.UUID,
) -> Policy:
    """Activate a policy version without creating a future-effective gap.

    A future version can be scheduled alongside the policy that is currently
    effective.  At its effective date ``get_active_policy`` selects the newer
    version, while existing submitted reports retain their own snapshot.
    """

    resolved_organization_id = _organization_id(organization_id)
    policy = _active_policy(db, policy_id, resolved_organization_id)
    now = datetime.now(UTC)
    effective_from = _as_datetime(policy.effective_from, field_name="effective_from", required=True)
    if effective_from <= now:
        # Keep any separately scheduled future version active.  It will become
        # selected naturally when its effective window opens.
        db.query(Policy).filter(
            Policy.organization_id == resolved_organization_id,
            Policy.is_active.is_(True),
            Policy.id != policy.id,
            Policy.is_deleted.is_(False),
            Policy.effective_from <= now,
        ).update({Policy.is_active: False}, synchronize_session=False)
    policy.is_active = True
    record_audit(
        db,
        "policies",
        str(policy.id),
        "activate",
        after={"is_active": True},
    )
    db.commit()
    return _active_policy(db, policy.id, resolved_organization_id)


def get_active_policy(
    db: Session,
    organization_id: str | uuid.UUID,
    at: datetime | None = None,
) -> Policy | None:
    """Return the active version that is effective at ``at`` (default: now)."""

    resolved_organization_id = _organization_id(organization_id)
    at = at or datetime.now(UTC)
    return db.scalar(
        select(Policy)
        .options(selectinload(Policy.rules))
        .where(
            Policy.organization_id == resolved_organization_id,
            Policy.is_active.is_(True),
            Policy.is_deleted.is_(False),
            Policy.effective_from <= at,
            (Policy.effective_to.is_(None) | (Policy.effective_to >= at)),
        )
        .order_by(Policy.effective_from.desc())
    )


def list_policies(db: Session, organization_id: str | uuid.UUID) -> list[Policy]:
    resolved_organization_id = _organization_id(organization_id)
    return list(
        db.scalars(
            select(Policy)
            .options(selectinload(Policy.rules))
            .where(
                Policy.organization_id == resolved_organization_id,
                Policy.is_deleted.is_(False),
            )
            .order_by(Policy.is_active.desc(), Policy.effective_from.desc(), Policy.created_at.desc())
        )
    )


def get_policy(
    db: Session,
    policy_id: str | uuid.UUID,
    organization_id: str | uuid.UUID,
) -> Policy:
    return _active_policy(db, policy_id, organization_id)


def attach_document(
    db: Session,
    policy_id: str | uuid.UUID,
    attachment_id: str | uuid.UUID,
    *,
    organization_id: str | uuid.UUID,
) -> Policy:
    policy = _active_policy(db, policy_id, organization_id)
    policy.uploaded_document_attachment_id = _uuid(attachment_id, field_name="attachment id")
    db.flush()
    return policy


def _lookup_names(db: Session, rules: list[PolicyRule]) -> tuple[dict[uuid.UUID, str], dict[uuid.UUID, str]]:
    category_ids = {rule.category_id for rule in rules if rule.category_id is not None}
    vendor_ids = {rule.vendor_id for rule in rules if rule.vendor_id is not None}
    categories = {
        category.id: category.name
        for category in db.scalars(select(ExpenseCategory).where(ExpenseCategory.id.in_(category_ids)))
    } if category_ids else {}
    vendors = {
        vendor.id: vendor.name
        for vendor in db.scalars(select(Vendor).where(Vendor.id.in_(vendor_ids)))
    } if vendor_ids else {}
    return categories, vendors


def policy_payload(db: Session, policy: Policy) -> dict[str, Any]:
    rules = [rule for rule in policy.rules if not rule.is_deleted]
    category_names, vendor_names = _lookup_names(db, rules)
    document = storage_service.get_attachment(db, policy.uploaded_document_attachment_id)
    now = datetime.now(UTC)
    effective_from = _as_datetime(policy.effective_from, field_name="effective_from", required=True)
    effective_to = _as_datetime(policy.effective_to, field_name="effective_to")
    if policy.is_active and effective_from > now:
        display_status = "scheduled"
    elif policy.is_active and (effective_to is None or effective_to >= now):
        display_status = "active"
    elif policy.is_active:
        display_status = "expired"
    else:
        display_status = "draft"
    return {
        "id": str(policy.id),
        "organization_id": str(policy.organization_id),
        "name": policy.name,
        "version_label": policy.version_label,
        "effective_from": policy.effective_from.isoformat() if policy.effective_from else None,
        "effective_to": policy.effective_to.isoformat() if policy.effective_to else None,
        "status": display_status,
        "document_url": storage_service.attachment_url(document),
        "document": storage_service.attachment_payload(document) if document else None,
        "rules": [
            {
                "id": str(rule.id),
                "category_id": str(rule.category_id) if rule.category_id else None,
                "category_name": category_names.get(rule.category_id) if rule.category_id else None,
                "vendor_id": str(rule.vendor_id) if rule.vendor_id else None,
                "vendor_name": vendor_names.get(rule.vendor_id) if rule.vendor_id else None,
                "max_per_day": float(rule.max_per_day) if rule.max_per_day is not None else None,
                "max_per_trip": float(rule.max_per_trip) if rule.max_per_trip is not None else None,
                "per_category_cap": float(rule.per_category_cap) if rule.per_category_cap is not None else None,
                "receipt_required_above": float(rule.receipt_required_above) if rule.receipt_required_above is not None else None,
            }
            for rule in rules
        ],
        "created_at": policy.created_at.isoformat() if policy.created_at else None,
        "updated_at": policy.updated_at.isoformat() if policy.updated_at else None,
    }
