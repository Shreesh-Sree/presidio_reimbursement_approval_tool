
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models.expense_report import ExpenseReport
from app.models.policy import Policy
from app.services.audit_service import record_audit


def create_draft(db: Session, employee_user_id, department_id, title):
    report = ExpenseReport(
        report_number=f"RPT-{int(datetime.utcnow().timestamp())}",
        employee_user_id=employee_user_id,
        department_id=department_id,
        title=title,
        status="draft",
        total_amount=Decimal("0"),
        last_saved_at=datetime.utcnow()
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    record_audit(db, "ExpenseReport", str(report.id), "insert", None, {"status": "draft"}, employee_user_id, {})
    return report


def submit_report(db: Session, report_id, user_id):
    report = db.query(ExpenseReport).filter(ExpenseReport.id == report_id).first()
    if not report:
        raise ValueError("Report not found")
    
    active_policy = db.query(Policy).filter(Policy.is_active == True).order_by(Policy.created_at.desc()).first()
    if not active_policy:
        raise ValueError("No active policy")
    
    before_state = {"status": report.status, "submitted_at": None}
    report.status = "submitted"
    report.submitted_at = datetime.utcnow()
    report.applied_policy_id = active_policy.id
    db.commit()
    db.refresh(report)
    record_audit(db, "ExpenseReport", str(report.id), "update", before_state, {"status": "submitted", "applied_policy_id": str(active_policy.id)}, user_id, {})
    return report


def withdraw_report(db: Session, report_id, user_id):
    report = db.query(ExpenseReport).filter(ExpenseReport.id == report_id).first()
    if not report:
        raise ValueError("Report not found")
    if report.status != "submitted":
        raise ValueError("Only submitted reports can be withdrawn")
    
    before_state = {"status": report.status}
    report.status = "draft"
    report.submitted_at = None
    db.commit()
    db.refresh(report)
    record_audit(db, "ExpenseReport", str(report.id), "update", before_state, {"status": "draft"}, user_id, {})
    return report


def list_reports(db: Session, org_id, filters=None):
    query = db.query(ExpenseReport).filter(ExpenseReport.is_deleted == False)
    if filters and "employee_id" in filters:
        query = query.filter(ExpenseReport.employee_user_id == filters["employee_id"])
    if filters and "status" in filters:
        query = query.filter(ExpenseReport.status == filters["status"])
    return query.all()


def get_report(db: Session, report_id):
    return db.query(ExpenseReport).filter(ExpenseReport.id == report_id, ExpenseReport.is_deleted == False).first()
