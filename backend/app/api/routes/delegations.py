"""Self-service approval delegation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.delegation_schemas import DelegationCreateInput, DelegationResponse
from app.core.database import get_db
from app.core.deps import require_permission
from app.models.user import User
from app.services import delegation_service


router = APIRouter(prefix="/api/delegations", tags=["delegations"])


def _payload(db: Session, delegation) -> dict[str, object]:
    delegate = db.get(User, delegation.delegate_user_id)
    return {
        "id": delegation.id,
        "delegator_user_id": delegation.delegator_user_id,
        "delegate_user_id": delegation.delegate_user_id,
        "delegate_name": delegate.full_name if delegate and not delegate.is_deleted else None,
        "start_date": delegation.start_date,
        "end_date": delegation.end_date,
        "scope": delegation.scope,
        "is_active": delegation.is_active,
        "remarks": delegation.remarks,
        "created_at": delegation.created_at,
        "updated_at": delegation.updated_at,
    }


def _raise_delegation_error(exc: Exception) -> None:
    if isinstance(exc, delegation_service.DelegationError):
        detail = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if detail == "Delegation not found" else status.HTTP_422_UNPROCESSABLE_CONTENT
        raise HTTPException(status_code=status_code, detail=detail) from exc
    raise exc


@router.get("", response_model=list[DelegationResponse])
async def list_my_delegations(
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("report:approve")),
):
    try:
        return [
            _payload(db, delegation)
            for delegation in delegation_service.list_delegations(
                db,
                user["user_id"],
                include_inactive=include_inactive,
            )
        ]
    except Exception as exc:
        _raise_delegation_error(exc)


@router.post("", response_model=DelegationResponse, status_code=status.HTTP_201_CREATED)
async def create_my_delegation(
    payload: DelegationCreateInput,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("report:approve")),
):
    try:
        delegation = delegation_service.create_delegation(
            db,
            delegator_user_id=user["user_id"],
            delegate_user_id=payload.delegate_user_id,
            start_date=payload.start_date,
            end_date=payload.end_date,
            scope=payload.scope,
            remarks=payload.remarks,
        )
        return _payload(db, delegation)
    except Exception as exc:
        _raise_delegation_error(exc)


@router.get("/candidates")
async def list_delegation_candidates(
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("report:approve")),
):
    try:
        return [
            {"id": str(candidate.id), "full_name": candidate.full_name}
            for candidate in delegation_service.list_eligible_delegates(db, user["user_id"])
        ]
    except Exception as exc:
        _raise_delegation_error(exc)


@router.delete("/{delegation_id}", response_model=DelegationResponse)
async def deactivate_my_delegation(
    delegation_id: str,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("report:approve")),
):
    try:
        delegation = delegation_service.deactivate_delegation(
            db,
            delegation_id,
            actor_user_id=user["user_id"],
        )
        return _payload(db, delegation)
    except Exception as exc:
        _raise_delegation_error(exc)
