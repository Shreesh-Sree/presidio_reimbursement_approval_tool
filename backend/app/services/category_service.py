from sqlalchemy.orm import Session
from app.models.expense_category import ExpenseCategory
from app.core.database import AuditLog


def create_category(db: Session, code: str, name: str, receipt_required: bool = True, max_amount: float = None):
    category = ExpenseCategory(code=code, name=name, receipt_required=receipt_required, max_amount=max_amount)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(db: Session, category_id: str, **kwargs):
    category = db.query(ExpenseCategory).filter(ExpenseCategory.id == category_id, ExpenseCategory.is_deleted == False).first()
    if not category:
        raise ValueError(f"Category {category_id} not found")
    for key, value in kwargs.items():
        if hasattr(category, key):
            setattr(category, key, value)
    db.commit()
    db.refresh(category)
    return category


def list_categories(db: Session):
    return db.query(ExpenseCategory).filter(ExpenseCategory.is_deleted == False).all()


def get_category(db: Session, category_id: str):
    return db.query(ExpenseCategory).filter(ExpenseCategory.id == category_id, ExpenseCategory.is_deleted == False).first()


def deactivate_category(db: Session, category_id: str):
    category = db.query(ExpenseCategory).filter(ExpenseCategory.id == category_id).first()
    if not category:
        raise ValueError(f"Category {category_id} not found")
    category.is_deleted = True
    db.commit()
    return category
