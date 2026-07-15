from datetime import date
from decimal import Decimal

from app.models.approval_level import ApprovalLevel
from app.models.expense_item import ExpenseItem
from app.models.notification import Notification
from app.models.payment_record import PaymentRecord
from app.models.user import User
from app.services import approval_service
from app.services.report_service import create_draft, submit_report


def _submitted_report(db, seeded_user, seeded_category):
    report = create_draft(db, seeded_user.id, seeded_user.department_id, "Client travel")
    db.add(
        ExpenseItem(
            expense_report_id=report.id,
            line_number=1,
            category_id=seeded_category.id,
            amount=Decimal("125.00"),
            original_amount=Decimal("125.00"),
            currency_code="USD",
            expense_date=date.today(),
            description="Client meeting travel",
        )
    )
    db.commit()
    return submit_report(db, report.id, seeded_user.id)


def _manager_for(db, seeded_user):
    manager = User(
        organization_id=seeded_user.organization_id,
        department_id=seeded_user.department_id,
        employee_number="M-001",
        username="manager",
        email="manager@example.com",
        password_hash=seeded_user.password_hash,
        full_name="Test Manager",
        status="active",
    )
    db.add(manager)
    db.flush()
    seeded_user.manager_user_id = manager.id
    db.commit()
    return manager


def test_report_routes_to_manager_and_final_approval_creates_payment(db, seeded_user, seeded_policy, seeded_category):
    manager = _manager_for(db, seeded_user)
    report = _submitted_report(db, seeded_user, seeded_category)

    levels = approval_service.init_workflow(db, report, seeded_user.id)

    assert len(levels) == 1
    assert levels[0].approver_user_id == manager.id
    assert levels[0].status == "pending"
    assert approval_service.queue_for_approver(db, manager.id)[0][1].id == report.id

    completed = approval_service.act_on_report(db, report.id, manager.id, "approve")

    assert completed.status == "approved_pending_payment"
    assert db.query(PaymentRecord).filter(PaymentRecord.expense_report_id == report.id).count() == 1
    assert (
        db.query(Notification)
        .filter(Notification.recipient_user_id == seeded_user.id, Notification.channel == "in_app")
        .count()
        == 1
    )


def test_send_back_cancels_pending_work_and_notifies_employee(db, seeded_user, seeded_policy, seeded_category):
    manager = _manager_for(db, seeded_user)
    report = _submitted_report(db, seeded_user, seeded_category)
    approval_service.init_workflow(db, report, seeded_user.id)

    returned = approval_service.act_on_report(db, report.id, manager.id, "send_back", "Please attach the hotel receipt")

    assert returned.status == "sent_back"
    level = db.query(ApprovalLevel).filter(ApprovalLevel.expense_report_id == report.id).one()
    assert level.status == "send_back"
    notification = (
        db.query(Notification)
        .filter(Notification.recipient_user_id == seeded_user.id, Notification.channel == "in_app")
        .one()
    )
    assert notification.payload_json["report_id"] == str(report.id)
