"""Category hierarchy operations used by policy administration and reports."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.expense_category import ExpenseCategory


class CategoryNotFoundError(LookupError):
    pass


class CategoryConflictError(ValueError):
    pass


def _uuid(value: str | uuid.UUID | None, *, field_name: str = "category id") -> uuid.UUID | None:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except ValueError as exc:
        raise CategoryNotFoundError(f"Invalid {field_name}") from exc


def _active_category(db: Session, category_id: str | uuid.UUID) -> ExpenseCategory:
    resolved_id = _uuid(category_id)
    category = db.scalar(
        select(ExpenseCategory).where(
            ExpenseCategory.id == resolved_id,
            ExpenseCategory.is_deleted.is_(False),
        )
    )
    if category is None:
        raise CategoryNotFoundError("Category not found")
    return category


def _ensure_code_available(db: Session, code: str, excluding_id: uuid.UUID | None = None) -> None:
    statement = select(ExpenseCategory).where(
        func.lower(ExpenseCategory.code) == code.lower(),
    )
    if excluding_id is not None:
        statement = statement.where(ExpenseCategory.id != excluding_id)
    if db.scalar(statement) is not None:
        raise CategoryConflictError("A category with that code already exists")


def _ensure_valid_parent(
    db: Session,
    *,
    category_id: uuid.UUID | None,
    parent_category_id: str | uuid.UUID | None,
) -> uuid.UUID | None:
    parent_id = _uuid(parent_category_id, field_name="parent category id")
    if parent_id is None:
        return None
    if category_id is not None and parent_id == category_id:
        raise CategoryConflictError("A category cannot be its own parent")
    parent = _active_category(db, parent_id)

    # Walk ancestors to prevent a cycle even when an existing subtree is moved.
    cursor: uuid.UUID | None = parent.parent_category_id
    while cursor is not None:
        if category_id is not None and cursor == category_id:
            raise CategoryConflictError("A category cannot be moved below one of its descendants")
        ancestor = db.scalar(select(ExpenseCategory).where(ExpenseCategory.id == cursor))
        cursor = ancestor.parent_category_id if ancestor is not None else None
    return parent.id


def create_category(
    db: Session,
    code: str,
    name: str,
    *,
    parent_id: str | uuid.UUID | None = None,
    description: str | None = None,
    receipt_required: bool = True,
    max_amount: Decimal | float | None = None,
) -> ExpenseCategory:
    normalized_code = code.strip().upper()
    normalized_name = name.strip()
    if not normalized_code or not normalized_name:
        raise CategoryConflictError("Category code and name are required")
    _ensure_code_available(db, normalized_code)
    category = ExpenseCategory(
        code=normalized_code,
        name=normalized_name,
        parent_category_id=_ensure_valid_parent(
            db, category_id=None, parent_category_id=parent_id
        ),
        description=description.strip() if description else None,
        receipt_required=receipt_required,
        max_amount=Decimal(str(max_amount)) if max_amount is not None else None,
    )
    db.add(category)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise CategoryConflictError("A category with that code already exists") from exc
    db.refresh(category)
    return category


def update_category(db: Session, category_id: str | uuid.UUID, **changes: Any) -> ExpenseCategory:
    category = _active_category(db, category_id)
    if "code" in changes and changes["code"] is not None:
        code = str(changes["code"]).strip().upper()
        if not code:
            raise CategoryConflictError("Category code cannot be empty")
        _ensure_code_available(db, code, excluding_id=category.id)
        category.code = code
    if "name" in changes and changes["name"] is not None:
        name = str(changes["name"]).strip()
        if not name:
            raise CategoryConflictError("Category name cannot be empty")
        category.name = name
    if "parent_id" in changes:
        category.parent_category_id = _ensure_valid_parent(
            db, category_id=category.id, parent_category_id=changes["parent_id"]
        )
    if "description" in changes:
        description = changes["description"]
        category.description = str(description).strip() if description else None
    if "receipt_required" in changes and changes["receipt_required"] is not None:
        category.receipt_required = bool(changes["receipt_required"])
    if "max_amount" in changes:
        value = changes["max_amount"]
        category.max_amount = Decimal(str(value)) if value is not None else None
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise CategoryConflictError("A category with that code already exists") from exc
    db.refresh(category)
    return category


def list_categories(db: Session, *, include_archived: bool = False) -> list[ExpenseCategory]:
    statement = select(ExpenseCategory).order_by(ExpenseCategory.name.asc())
    if not include_archived:
        statement = statement.where(ExpenseCategory.is_deleted.is_(False))
    return list(db.scalars(statement))


def get_category(db: Session, category_id: str | uuid.UUID) -> ExpenseCategory:
    return _active_category(db, category_id)


def deactivate_category(db: Session, category_id: str | uuid.UUID) -> ExpenseCategory:
    category = _active_category(db, category_id)
    child = db.scalar(
        select(ExpenseCategory.id).where(
            ExpenseCategory.parent_category_id == category.id,
            ExpenseCategory.is_deleted.is_(False),
        )
    )
    if child is not None:
        raise CategoryConflictError("Move or deactivate child categories before deleting this category")
    category.is_deleted = True
    db.commit()
    db.refresh(category)
    return category


def restore_category(db: Session, category_id: str | uuid.UUID) -> ExpenseCategory:
    category_id = _uuid(category_id)
    category = db.scalar(select(ExpenseCategory).where(ExpenseCategory.id == category_id))
    if category is None:
        raise CategoryNotFoundError("Category not found")
    category.is_deleted = False
    category.deleted_at = None
    db.commit()
    db.refresh(category)
    return category


def permanently_delete_category(db: Session, category_id: str | uuid.UUID) -> None:
    category_id = _uuid(category_id)
    category = db.scalar(select(ExpenseCategory).where(ExpenseCategory.id == category_id))
    if category is None:
        raise CategoryNotFoundError("Category not found")
    if not category.is_deleted:
        raise CategoryConflictError("Archive the category before permanently deleting it")
    db.delete(category)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise CategoryConflictError("This archived category is referenced by historical records and cannot be permanently deleted") from exc


def category_payload(category: ExpenseCategory, children: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "id": str(category.id),
        "code": category.code,
        "name": category.name,
        "parent_id": str(category.parent_category_id) if category.parent_category_id else None,
        "description": category.description,
        "receipt_required": category.receipt_required,
        "max_amount": float(category.max_amount) if category.max_amount is not None else None,
        "is_deleted": category.is_deleted,
        "children": children or [],
    }


def category_tree_payload(categories: list[ExpenseCategory]) -> list[dict[str, Any]]:
    """Return a stable, nested payload without relying on a mapper relationship."""

    nodes = {category.id: category_payload(category) for category in categories}
    roots: list[dict[str, Any]] = []
    for category in categories:
        node = nodes[category.id]
        if category.parent_category_id in nodes:
            nodes[category.parent_category_id]["children"].append(node)
        else:
            roots.append(node)
    return roots
