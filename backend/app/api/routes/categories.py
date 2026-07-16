"""Expense category hierarchy API."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_permission
from app.services import category_service


router = APIRouter(prefix="/api/categories", tags=["categories"])


class CategoryCreateInput(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=150)
    parent_id: str | None = None
    description: str | None = Field(default=None, max_length=500)
    receipt_required: bool = True
    max_amount: Decimal | None = Field(default=None, ge=0)


class CategoryUpdateInput(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=100)
    name: str | None = Field(default=None, min_length=1, max_length=150)
    parent_id: str | None = None
    description: str | None = Field(default=None, max_length=500)
    receipt_required: bool | None = None
    max_amount: Decimal | None = Field(default=None, ge=0)


def _category_error(exc: Exception) -> None:
    if isinstance(exc, category_service.CategoryNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, category_service.CategoryConflictError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    raise exc


@router.get("")
async def list_categories(
    include_archived: bool = False,
    db: Session = Depends(get_db),
    _user: dict[str, str] = Depends(require_permission("category:read")),
):
    categories = category_service.list_categories(db, include_archived=include_archived)
    return category_service.category_tree_payload(categories) if not include_archived else [category_service.category_payload(category) for category in categories]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: CategoryCreateInput,
    db: Session = Depends(get_db),
    _user: dict[str, str] = Depends(require_permission("category:manage")),
):
    try:
        category = category_service.create_category(db, **payload.model_dump())
        return category_service.category_payload(category)
    except Exception as exc:
        _category_error(exc)


@router.get("/{category_id}")
async def get_category(
    category_id: str,
    db: Session = Depends(get_db),
    _user: dict[str, str] = Depends(require_permission("category:read")),
):
    try:
        return category_service.category_payload(category_service.get_category(db, category_id))
    except Exception as exc:
        _category_error(exc)


@router.patch("/{category_id}")
async def update_category(
    category_id: str,
    payload: CategoryUpdateInput,
    db: Session = Depends(get_db),
    _user: dict[str, str] = Depends(require_permission("category:manage")),
):
    try:
        changes: dict[str, Any] = payload.model_dump(exclude_unset=True)
        category = category_service.update_category(db, category_id, **changes)
        return category_service.category_payload(category)
    except Exception as exc:
        _category_error(exc)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: str,
    db: Session = Depends(get_db),
    _user: dict[str, str] = Depends(require_permission("category:manage")),
) -> Response:
    try:
        category_service.deactivate_category(db, category_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        _category_error(exc)


@router.post("/{category_id}/restore")
async def restore_category(category_id: str, db: Session = Depends(get_db), _user: dict[str, str] = Depends(require_permission("category:manage"))):
    try:
        return category_service.category_payload(category_service.restore_category(db, category_id))
    except Exception as exc:
        _category_error(exc)


@router.delete("/{category_id}/permanent", status_code=status.HTTP_204_NO_CONTENT)
async def permanently_delete_category(category_id: str, db: Session = Depends(get_db), _user: dict[str, str] = Depends(require_permission("category:manage"))) -> Response:
    try:
        category_service.permanently_delete_category(db, category_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        _category_error(exc)
