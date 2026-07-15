"""Temporary approval delegation with explicit ownership and cycle protection."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.delegation import Delegation
from app.models.user import User
from app.services.audit_service import record_audit
from app.services import user_service


APPROVAL_SCOPES = frozenset({"all", "approval"})
VALID_SCOPES = frozenset({"all", "approval"})


class DelegationError(ValueError):
    """A user-correctable delegation configuration error."""


def utcnow() -> datetime:
    return datetime.now(UTC)


def _as_uuid(value: uuid.UUID | str, *, field_name: str) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise DelegationError(f"Invalid {field_name}") from exc


def _as_utc(value: datetime, *, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise DelegationError(f"Invalid {field_name}")
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _active_user(db: Session, user_id: uuid.UUID, *, field_name: str) -> User:
    user = (
        db.query(User)
        .filter(User.id == user_id, User.is_deleted.is_(False), User.status == "active")
        .first()
    )
    if user is None:
        raise DelegationError(f"{field_name} must be an active user")
    return user


def is_approval_eligible(db: Session, user_id: uuid.UUID) -> bool:
    """Whether a user can make a protected report-approval decision."""

    permissions = set(user_service.permission_codes_for_user(db, user_id))
    return "*" in permissions or "report:approve" in permissions


def _overlaps(start_date: datetime, end_date: datetime):
    """SQL predicate for any interval intersecting the requested interval."""

    return and_(Delegation.start_date <= end_date, Delegation.end_date >= start_date)


def _would_create_cycle(
    db: Session,
    *,
    delegator_id: uuid.UUID,
    delegate_id: uuid.UUID,
    start_date: datetime,
    end_date: datetime,
) -> bool:
    """Detect delegation loops across overlapping approval delegation windows."""

    frontier = [delegate_id]
    visited: set[uuid.UUID] = set()
    while frontier:
        current = frontier.pop()
        if current == delegator_id:
            return True
        if current in visited:
            continue
        visited.add(current)
        children = (
            db.query(Delegation.delegate_user_id)
            .filter(
                Delegation.delegator_user_id == current,
                Delegation.scope.in_(APPROVAL_SCOPES),
                Delegation.is_active.is_(True),
                Delegation.is_deleted.is_(False),
                _overlaps(start_date, end_date),
            )
            .all()
        )
        frontier.extend(child[0] for child in children if child[0] not in visited)
    return False


def _scope_conflicts(existing_scope: str, requested_scope: str) -> bool:
    # Both supported scopes apply to approvals. Keep one active assignment per
    # source/time window so a manager never unknowingly has two substitutes.
    return existing_scope in APPROVAL_SCOPES and requested_scope in APPROVAL_SCOPES


def create_delegation(
    db: Session,
    *,
    delegator_user_id: uuid.UUID | str,
    delegate_user_id: uuid.UUID | str,
    start_date: datetime,
    end_date: datetime,
    scope: str = "approval",
    remarks: str | None = None,
) -> Delegation:
    """Create an approval delegation inside one organization and time range."""

    delegator_id = _as_uuid(delegator_user_id, field_name="delegator user id")
    delegate_id = _as_uuid(delegate_user_id, field_name="delegate user id")
    normalized_scope = scope.strip().lower()
    if normalized_scope not in VALID_SCOPES:
        raise DelegationError("scope must be one of: all, approval")
    if delegator_id == delegate_id:
        raise DelegationError("You cannot delegate approval to yourself")
    starts_at = _as_utc(start_date, field_name="start date")
    ends_at = _as_utc(end_date, field_name="end date")
    if ends_at <= starts_at:
        raise DelegationError("end date must be after start date")

    delegator = _active_user(db, delegator_id, field_name="Delegator")
    delegate = _active_user(db, delegate_id, field_name="Delegate")
    if delegator.organization_id != delegate.organization_id:
        raise DelegationError("Delegate must belong to the same organization")
    if not is_approval_eligible(db, delegator.id):
        raise DelegationError("Delegator must have report approval permission")
    if not is_approval_eligible(db, delegate.id):
        raise DelegationError("Delegate must have report approval permission")

    overlapping = (
        db.query(Delegation)
        .filter(
            Delegation.delegator_user_id == delegator.id,
            Delegation.is_active.is_(True),
            Delegation.is_deleted.is_(False),
            _overlaps(starts_at, ends_at),
        )
        .all()
    )
    if any(_scope_conflicts(entry.scope, normalized_scope) for entry in overlapping):
        raise DelegationError("An overlapping approval delegation already exists")
    if _would_create_cycle(
        db,
        delegator_id=delegator.id,
        delegate_id=delegate.id,
        start_date=starts_at,
        end_date=ends_at,
    ):
        raise DelegationError("Delegation would create an approval cycle")

    delegation = Delegation(
        delegator_user_id=delegator.id,
        delegate_user_id=delegate.id,
        start_date=starts_at,
        end_date=ends_at,
        scope=normalized_scope,
        remarks=(remarks or "").strip() or None,
        is_active=True,
    )
    db.add(delegation)
    db.flush()
    # A manager can create delegation after a report is already pending. Move
    # those live tasks in the same transaction so queue visibility and action
    # authorization change together.
    from app.services import approval_service

    approval_service.synchronize_pending_delegations(
        db,
        user_id=delegator.id,
        performed_by=delegator.id,
    )
    record_audit(
        db,
        "delegations",
        str(delegation.id),
        "create",
        after={
            "delegator_user_id": str(delegator.id),
            "delegate_user_id": str(delegate.id),
            "start_date": starts_at.isoformat(),
            "end_date": ends_at.isoformat(),
            "scope": normalized_scope,
        },
        performed_by=str(delegator.id),
    )
    db.commit()
    db.refresh(delegation)
    return delegation


def list_delegations(
    db: Session,
    delegator_user_id: uuid.UUID | str,
    *,
    include_inactive: bool = False,
) -> list[Delegation]:
    delegator_id = _as_uuid(delegator_user_id, field_name="delegator user id")
    query = db.query(Delegation).filter(
        Delegation.delegator_user_id == delegator_id,
        Delegation.is_deleted.is_(False),
    )
    if not include_inactive:
        query = query.filter(Delegation.is_active.is_(True), Delegation.end_date >= utcnow())
    return query.order_by(Delegation.start_date.desc(), Delegation.created_at.desc()).all()


def deactivate_delegation(
    db: Session,
    delegation_id: uuid.UUID | str,
    *,
    actor_user_id: uuid.UUID | str,
) -> Delegation:
    delegation_uuid = _as_uuid(delegation_id, field_name="delegation id")
    actor_id = _as_uuid(actor_user_id, field_name="actor user id")
    delegation = (
        db.query(Delegation)
        .filter(Delegation.id == delegation_uuid, Delegation.is_deleted.is_(False))
        .first()
    )
    if delegation is None:
        raise DelegationError("Delegation not found")
    if delegation.delegator_user_id != actor_id:
        raise DelegationError("Only the delegator can deactivate this delegation")
    if delegation.is_active:
        delegation.is_active = False
        # Restore still-pending, non-escalated tasks to their original owner
        # before the cancellation becomes visible. The resolver sees the
        # in-transaction inactive flag and clears the delegation assignment.
        from app.services import approval_service

        approval_service.synchronize_pending_delegations(
            db,
            user_id=delegation.delegator_user_id,
            performed_by=actor_id,
        )
        record_audit(
            db,
            "delegations",
            str(delegation.id),
            "deactivate",
            before={"is_active": True},
            after={"is_active": False},
            performed_by=str(actor_id),
        )
        db.commit()
        db.refresh(delegation)
    return delegation


def active_approval_delegation(
    db: Session,
    delegator_user_id: uuid.UUID | str,
    *,
    at: datetime | None = None,
) -> Delegation | None:
    """Return the one active eligible substitute at a given instant."""

    delegator_id = _as_uuid(delegator_user_id, field_name="delegator user id")
    moment = _as_utc(at or utcnow(), field_name="delegation lookup time")
    delegation = (
        db.query(Delegation)
        .filter(
            Delegation.delegator_user_id == delegator_id,
            Delegation.scope.in_(APPROVAL_SCOPES),
            Delegation.is_active.is_(True),
            Delegation.is_deleted.is_(False),
            Delegation.start_date <= moment,
            Delegation.end_date >= moment,
        )
        .order_by(Delegation.created_at.desc(), Delegation.id.desc())
        .first()
    )
    if delegation is None:
        return None
    try:
        delegator = _active_user(db, delegation.delegator_user_id, field_name="Delegator")
        delegate = _active_user(db, delegation.delegate_user_id, field_name="Delegate")
    except DelegationError:
        return None
    if delegator.organization_id != delegate.organization_id or not is_approval_eligible(db, delegate.id):
        return None
    return delegation


def resolve_approval_assignee(
    db: Session,
    original_approver_user_id: uuid.UUID | str,
    *,
    at: datetime | None = None,
) -> tuple[uuid.UUID, Delegation | None]:
    """Resolve a current delegation without hiding the original approver."""

    original_id = _as_uuid(original_approver_user_id, field_name="original approver user id")
    if delegation := active_approval_delegation(db, original_id, at=at):
        return delegation.delegate_user_id, delegation
    return original_id, None


def list_eligible_delegates(
    db: Session,
    delegator_user_id: uuid.UUID | str,
) -> list[User]:
    """Return same-organization active approvers, excluding the delegator."""

    delegator_id = _as_uuid(delegator_user_id, field_name="delegator user id")
    delegator = _active_user(db, delegator_id, field_name="Delegator")
    candidates = (
        db.query(User)
        .filter(
            User.organization_id == delegator.organization_id,
            User.id != delegator.id,
            User.is_deleted.is_(False),
            User.status == "active",
        )
        .order_by(User.full_name.asc(), User.email.asc())
        .all()
    )
    return [candidate for candidate in candidates if is_approval_eligible(db, candidate.id)]
