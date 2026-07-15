from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import require_permission, get_current_user
from app.services import report_service, item_service, validation_service, approval_service

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("")
async def create_report(title: str, db: Session = Depends(get_db), user = Depends(require_permission("report:create"))):
    report = report_service.create_draft(db, user["user_id"], "dept-id", title)
    return {"id": str(report.id), "status": report.status}


@router.get("")
async def list_user_reports(db: Session = Depends(get_db), user = Depends(require_permission("report:read"))):
    reports = report_service.list_reports(db, "org-id", {"employee_id": user["user_id"]})
    return [{"id": str(r.id), "status": r.status, "total": str(r.total_amount)} for r in reports]


@router.get("/{report_id}")
async def get_report(report_id: str, db: Session = Depends(get_db), user = Depends(require_permission("report:read"))):
    report = report_service.get_report(db, report_id)
    return {"id": str(report.id), "status": report.status, "total": str(report.total_amount)}


@router.post("/{report_id}/submit")
async def submit_report(report_id: str, db: Session = Depends(get_db), user = Depends(require_permission("report:create"))):
    report = report_service.submit_report(db, report_id, user["user_id"])
    violations = validation_service.validate_report(db, report)
    if violations:
        return {"status": "blocked", "violations": violations}
    approval_service.init_workflow(db, report)
    return {"status": "submitted", "applied_policy": str(report.applied_policy_id)}


@router.post("/{report_id}/withdraw")
async def withdraw_report(report_id: str, db: Session = Depends(get_db), user = Depends(require_permission("report:create"))):
    report = report_service.withdraw_report(db, report_id, user["user_id"])
    return {"status": "withdrawn"}


@router.post("/{report_id}/items")
async def add_item(report_id: str, category_id: str, vendor_id: str, amount: float, description: str, db: Session = Depends(get_db), user = Depends(require_permission("report:create"))):
    from decimal import Decimal
    item = item_service.add_item(db, report_id, category_id, vendor_id, Decimal(str(amount)), description, user["user_id"])
    return {"item_id": str(item.id), "line_number": item.line_number}


@router.get("/{report_id}/items")
async def list_items(report_id: str, db: Session = Depends(get_db), user = Depends(require_permission("report:read"))):
    items = item_service.list_items(db, report_id)
    return [{"id": str(i.id), "amount": str(i.amount), "description": i.description} for i in items]
