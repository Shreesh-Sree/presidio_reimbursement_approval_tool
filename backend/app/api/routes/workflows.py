"""Tenant-scoped workflow-rule administration endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.workflow_schemas import WorkflowRuleCreateInput, WorkflowRuleUpdateInput
from app.core.database import get_db
from app.core.deps import require_permission
from app.services import workflow_service


router = APIRouter(prefix="/api/workflows", tags=["workflows"])


def _scope(current_user: dict[str, object]) -> tuple[UUID, UUID]:
    return UUID(str(current_user["organization_id"])), UUID(str(current_user["user_id"]))


def _raise_workflow_error(exc: Exception) -> None:
    if isinstance(exc, workflow_service.WorkflowRuleNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(
        exc,
        (workflow_service.WorkflowRuleConflictError, workflow_service.WorkflowRuleValidationError),
    ):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    raise exc


@router.get("")
async def list_workflows(
    db: Session = Depends(get_db),
    current_user: dict[str, object] = Depends(require_permission("workflow:manage")),
):
    organization_id, _ = _scope(current_user)
    return [
        workflow_service.workflow_rule_payload(rule)
        for rule in workflow_service.list_workflow_rules(db, organization_id)
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_workflow(
    payload: WorkflowRuleCreateInput,
    db: Session = Depends(get_db),
    current_user: dict[str, object] = Depends(require_permission("workflow:manage")),
):
    organization_id, actor_user_id = _scope(current_user)
    try:
        rule = workflow_service.create_workflow_rule(
            db,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            name=payload.name,
            conditions=payload.conditions.model_dump(exclude_none=True),
            approval_chain=[step.model_dump(exclude_none=True) for step in payload.approval_chain],
            priority=payload.priority,
            is_active=payload.is_active,
        )
        return workflow_service.workflow_rule_payload(rule)
    except Exception as exc:
        _raise_workflow_error(exc)


@router.get("/{rule_id}")
async def get_workflow(
    rule_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict[str, object] = Depends(require_permission("workflow:manage")),
):
    organization_id, _ = _scope(current_user)
    try:
        rule = workflow_service.get_workflow_rule(db, rule_id, organization_id)
        return workflow_service.workflow_rule_payload(rule)
    except Exception as exc:
        _raise_workflow_error(exc)


@router.patch("/{rule_id}")
async def update_workflow(
    rule_id: UUID,
    payload: WorkflowRuleUpdateInput,
    db: Session = Depends(get_db),
    current_user: dict[str, object] = Depends(require_permission("workflow:manage")),
):
    organization_id, actor_user_id = _scope(current_user)
    changes = payload.model_dump(exclude_unset=True, exclude_none=False)
    if "conditions" in changes and changes["conditions"] is not None:
        changes["conditions"] = payload.conditions.model_dump(exclude_none=True)
    if "approval_chain" in changes and changes["approval_chain"] is not None:
        changes["approval_chain"] = [step.model_dump(exclude_none=True) for step in payload.approval_chain or []]
    try:
        rule = workflow_service.update_workflow_rule(
            db,
            rule_id,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            changes=changes,
        )
        return workflow_service.workflow_rule_payload(rule)
    except Exception as exc:
        _raise_workflow_error(exc)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    rule_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict[str, object] = Depends(require_permission("workflow:manage")),
) -> Response:
    organization_id, actor_user_id = _scope(current_user)
    try:
        workflow_service.delete_workflow_rule(
            db,
            rule_id,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        _raise_workflow_error(exc)
