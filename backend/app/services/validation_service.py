from decimal import Decimal
from sqlalchemy.orm import Session
from app.models.expense_report import ExpenseReport
from app.models.expense_item import ExpenseItem


def validate_report(db, report):
    if not report.applied_policy_id:
        return []
    violations = []
    for item in report.items:
        if not item.is_deleted and item.amount > 10000:
            item.is_policy_violated = True
            violations.append("Amount exceeds limit")
    return violations
