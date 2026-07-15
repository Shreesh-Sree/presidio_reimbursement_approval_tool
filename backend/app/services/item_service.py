from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import datetime
from app.models.expense_item import ExpenseItem
from app.models.expense_report import ExpenseReport


def add_line_item(db: Session, report_id: str, category_id: str, merchant_name: str, amount: float, expense_date: str):
    """Add a line item to a report."""
    report = db.query(ExpenseReport).filter(ExpenseReport.id == report_id).first()
    if not report:
        raise ValueError(f"Report {report_id} not found")
    
    # Get next line number
    max_line = db.query(ExpenseItem).filter(ExpenseItem.expense_report_id == report_id).count()
    line_number = max_line + 1
    
    item = ExpenseItem(
        expense_report_id=report_id,
        line_number=line_number,
        category_id=category_id,
        merchant_name=merchant_name,
        amount=Decimal(str(amount)),
        expense_date=expense_date,
    )
    db.add(item)
    db.flush()
    
    # Recompute report total
    _recompute_report_total(db, report_id)
    db.commit()
    db.refresh(item)
    return item


def update_line_item(db: Session, item_id: str, **kwargs):
    """Update a line item."""
    item = db.query(ExpenseItem).filter(ExpenseItem.id == item_id, ExpenseItem.is_deleted == False).first()
    if not item:
        raise ValueError(f"Item {item_id} not found")
    
    for key, value in kwargs.items():
        if hasattr(item, key) and key != "id":
            setattr(item, key, value)
    
    db.flush()
    _recompute_report_total(db, item.expense_report_id)
    db.commit()
    db.refresh(item)
    return item


def delete_line_item(db: Session, item_id: str):
    """Soft-delete a line item."""
    item = db.query(ExpenseItem).filter(ExpenseItem.id == item_id).first()
    if not item:
        raise ValueError(f"Item {item_id} not found")
    
    item.is_deleted = True
    db.flush()
    _recompute_report_total(db, item.expense_report_id)
    db.commit()
    return item


def _recompute_report_total(db: Session, report_id: str):
    """Recalculate report total from non-deleted items."""
    total = db.query(ExpenseItem).filter(
        ExpenseItem.expense_report_id == report_id,
        ExpenseItem.is_deleted == False,
    ).with_entities(
        db.func.sum(ExpenseItem.amount)
    ).scalar() or Decimal(0)
    
    report = db.query(ExpenseReport).filter(ExpenseReport.id == report_id).first()
    report.total_amount = float(total)
