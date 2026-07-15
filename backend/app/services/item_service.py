
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models.expense_item import ExpenseItem
from app.models.expense_report import ExpenseReport
from app.services.audit_service import record_audit


def add_item(db: Session, report_id, category_id, vendor_id, amount, description, user_id):
    report = db.query(ExpenseReport).filter(ExpenseReport.id == report_id).first()
    if not report:
        raise ValueError("Report not found")
    if report.status != "draft":
        raise ValueError("Can only add items to draft reports")
    
    item = ExpenseItem(
        expense_report_id=report_id,
        expense_category_id=category_id,
        vendor_id=vendor_id,
        amount=amount,
        description=description,
        line_number=len(report.items) + 1 if report.items else 1
    )
    db.add(item)
    report.total_amount = (report.total_amount or Decimal("0")) + amount
    db.commit()
    db.refresh(item)
    record_audit(db, "ExpenseItem", str(item.id), "insert", None, {"amount": str(amount)}, user_id, {})
    return item


def update_item(db: Session, item_id, amount, description, user_id):
    item = db.query(ExpenseItem).filter(ExpenseItem.id == item_id).first()
    if not item:
        raise ValueError("Item not found")
    
    report = item.expense_report
    if report.status != "draft":
        raise ValueError("Can only edit items in draft reports")
    
    before_state = {"amount": str(item.amount), "description": item.description}
    report.total_amount = (report.total_amount or Decimal("0")) - item.amount + amount
    item.amount = amount
    item.description = description
    db.commit()
    db.refresh(item)
    record_audit(db, "ExpenseItem", str(item.id), "update", before_state, {"amount": str(amount), "description": description}, user_id, {})
    return item


def delete_item(db: Session, item_id, user_id):
    item = db.query(ExpenseItem).filter(ExpenseItem.id == item_id).first()
    if not item:
        raise ValueError("Item not found")
    
    report = item.expense_report
    report.total_amount = (report.total_amount or Decimal("0")) - item.amount
    item.is_deleted = True
    item.deleted_at = datetime.utcnow()
    db.commit()
    record_audit(db, "ExpenseItem", str(item.id), "delete", {"amount": str(item.amount)}, None, user_id, {})


def list_items(db: Session, report_id):
    return db.query(ExpenseItem).filter(ExpenseItem.expense_report_id == report_id, ExpenseItem.is_deleted == False).all()
