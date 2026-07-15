from datetime import datetime
from sqlalchemy.orm import Session
from app.models.approval_level import ApprovalLevel
from app.models.approval_history import ApprovalHistory


def init_workflow(db, report):
    approval = ApprovalLevel(expense_report_id=report.id, approver_user_id=report.employee_user_id, level_number=1, status="pending")
    db.add(approval)
    db.commit()
    return approval


def approve(db, approval_id, user_id, remarks=None):
    approval = db.query(ApprovalLevel).filter(ApprovalLevel.id == approval_id).first()
    approval.status = "approved"
    approval.decision_date = datetime.utcnow()
    db.commit()
    return approval
