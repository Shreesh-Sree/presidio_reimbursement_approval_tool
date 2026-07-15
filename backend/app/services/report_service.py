from sqlalchemy.orm import Session
from datetime import datetime
from app.models.expense_report import ExpenseReport
from app.models.policy import Policy
import uuid


def create_draft_report(db: Session, employee_user_id: str, department_id: str, title: str):
    """Create a new draft report."""
    report = ExpenseReport(
        report_number=f"RPT-{uuid.uuid4().hex[:8]}",
        employee_user_id=employee_user_id,
        department_id=department_id,
        title=title,
        status="draft",
        total_amount=0,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def submit_report(db: Session, report_id: str):
    """Submit a report (snapshot active policy, set submitted_at)."""
    report = db.query(ExpenseReport).filter(ExpenseReport.id == report_id, ExpenseReport.is_deleted == False).first()
    if not report:
        raise ValueError(f"Report {report_id} not found")
    
    # Snapshot active policy
    active_policy = db.query(Policy).filter(Policy.is_active == True).first()
    if not active_policy:
        raise ValueError("No active policy to snapshot")
    
    report.applied_policy_id = active_policy.id
    report.status = "submitted"
    report.submitted_at = datetime.utcnow().isoformat()
    db.commit()
    db.refresh(report)
    return report


def withdraw_report(db: Session, report_id: str):
    """Withdraw a report (revert to draft if submitted)."""
    report = db.query(ExpenseReport).filter(ExpenseReport.id == report_id, ExpenseReport.is_deleted == False).first()
    if not report:
        raise ValueError(f"Report {report_id} not found")
    
    if report.status != "submitted":
        raise ValueError(f"Cannot withdraw report in {report.status} status")
    
    report.status = "draft"
    report.submitted_at = None
    db.commit()
    db.refresh(report)
    return report


def list_reports(db: Session, user_id: str = None, department_id: str = None):
    """List reports filtered by user/department."""
    query = db.query(ExpenseReport).filter(ExpenseReport.is_deleted == False)
    if user_id:
        query = query.filter(ExpenseReport.employee_user_id == user_id)
    if department_id:
        query = query.filter(ExpenseReport.department_id == department_id)
    return query.all()


def get_report(db: Session, report_id: str):
    """Get a specific report."""
    return db.query(ExpenseReport).filter(ExpenseReport.id == report_id, ExpenseReport.is_deleted == False).first()
