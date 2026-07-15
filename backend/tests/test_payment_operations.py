"""Finance payment lifecycle coverage for approved reimbursement reports."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.models.department import Department
from app.models.expense_report import ExpenseReport
from app.models.organization import Organization
from app.models.payment_record import PaymentRecord
from app.models.user import User
from app.services import payment_service


PASSWORD = "correct-horse-battery-staple"


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login(client, email: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return _headers(response.json()["access_token"])


def _approved_payment(client) -> tuple[dict[str, str], str, str]:
    """Create the smallest complete report/approval flow and return its payment."""

    bootstrap = client.post(
        "/api/auth/bootstrap",
        json={
            "organization_name": "Payment Test Co",
            "organization_code": "PAYTEST",
            "department_name": "Finance",
            "department_code": "FIN",
            "full_name": "Finance Admin",
            "email": "finance-admin@example.com",
            "password": PASSWORD,
        },
    )
    assert bootstrap.status_code == 201, bootstrap.text
    admin_headers = _headers(bootstrap.json()["access_token"])

    manager = client.post(
        "/api/users",
        headers=admin_headers,
        json={
            "full_name": "Approving Manager",
            "email": "payment-manager@example.com",
            "password": PASSWORD,
            "roles": ["employee", "approver"],
        },
    )
    assert manager.status_code == 201, manager.text
    employee = client.post(
        "/api/users",
        headers=admin_headers,
        json={
            "full_name": "Expense Employee",
            "email": "payment-employee@example.com",
            "password": PASSWORD,
            "roles": ["employee"],
            "manager_id": manager.json()["id"],
        },
    )
    assert employee.status_code == 201, employee.text

    category = client.post(
        "/api/categories",
        headers=admin_headers,
        json={"code": "TRAVEL", "name": "Travel"},
    )
    assert category.status_code == 201, category.text
    policy = client.post(
        "/api/policies",
        headers=admin_headers,
        json={
            "name": "Payment policy",
            "version_label": "v1",
            "effective_from": datetime.now(UTC).isoformat(),
            "rules": [{"category_id": category.json()["id"], "max_per_trip": 500}],
        },
    )
    assert policy.status_code == 201, policy.text
    assert client.post(f"/api/policies/{policy.json()['id']}/activate", headers=admin_headers).status_code == 200

    employee_headers = _login(client, "payment-employee@example.com")
    report = client.post("/api/reports", headers=employee_headers, json={"title": "Client travel", "currency": "USD"})
    assert report.status_code == 201, report.text
    report_id = report.json()["id"]
    item = client.post(
        f"/api/reports/{report_id}/items",
        headers=employee_headers,
        json={
            "category_id": category.json()["id"],
            "amount": "125.00",
            "currency": "USD",
            "expense_date": "2026-07-15",
        },
    )
    assert item.status_code == 201, item.text
    assert client.post(f"/api/reports/{report_id}/submit", headers=employee_headers).status_code == 200

    manager_headers = _login(client, "payment-manager@example.com")
    approved = client.post(
        f"/api/approvals/{report_id}/approve",
        headers=manager_headers,
        json={"remarks": "Approved for payment"},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved_pending_payment"

    queue = client.get("/api/payments", headers=admin_headers)
    assert queue.status_code == 200, queue.text
    assert len(queue.json()["items"]) == 1
    payment = queue.json()["items"][0]
    assert payment["status"] == "pending"
    assert payment["report_id"] == report_id
    return admin_headers, payment["id"], report_id


def test_finance_can_batch_export_and_mark_a_payment_paid(client):
    admin_headers, payment_id, report_id = _approved_payment(client)

    batch = client.post(
        "/api/payments/batches",
        headers=admin_headers,
        json={"payment_ids": [payment_id], "remarks": "July reimbursement run"},
    )
    assert batch.status_code == 201, batch.text
    assert batch.json()["status"] == "created"
    assert batch.json()["payment_count"] == 1
    batch_id = batch.json()["id"]

    exported = client.post(f"/api/payments/batches/{batch_id}/export", headers=admin_headers)
    assert exported.status_code == 200, exported.text
    assert exported.headers["content-type"].startswith("text/csv")
    assert "payment_reference" in exported.text
    assert "125.00" in exported.text

    exported_payment = client.get(f"/api/payments/{payment_id}", headers=admin_headers)
    assert exported_payment.status_code == 200, exported_payment.text
    assert exported_payment.json()["status"] == "exported"
    assert [event["event_type"] for event in exported_payment.json()["history"]] == [
        "created",
        "batched",
        "exported",
    ]

    paid = client.post(
        f"/api/payments/{payment_id}/mark-paid",
        headers=admin_headers,
        json={"provider_reference": "BANK-TRANSFER-001", "payment_date": "2026-07-20"},
    )
    assert paid.status_code == 200, paid.text
    assert paid.json()["status"] == "paid"
    assert paid.json()["provider_reference"] == "BANK-TRANSFER-001"
    assert paid.json()["payment_date"] == "2026-07-20"
    assert paid.json()["history"][-1]["event_type"] == "paid"

    report = client.get(f"/api/reports/{report_id}", headers=admin_headers)
    assert report.status_code == 200, report.text
    assert report.json()["status"] == "paid"
    assert report.json()["payment"]["status"] == "paid"
    assert "bank_detail" not in report.json()["payment"]


def test_failed_payment_is_organization_scoped_and_cannot_skip_export(client, db):
    admin_headers, payment_id, _report_id = _approved_payment(client)

    skipped = client.post(
        f"/api/payments/{payment_id}/mark-paid",
        headers=admin_headers,
        json={"provider_reference": "BANK-TRANSFER-TOO-EARLY"},
    )
    assert skipped.status_code == 422
    assert "exported" in skipped.json()["detail"].lower()

    batch = client.post(
        "/api/payments/batches",
        headers=admin_headers,
        json={"payment_ids": [payment_id]},
    )
    assert batch.status_code == 201, batch.text
    before_export = client.post(
        f"/api/payments/{payment_id}/mark-failed",
        headers=admin_headers,
        json={"failure_reason": "This must wait for an export outcome"},
    )
    assert before_export.status_code == 422
    assert "exported" in before_export.json()["detail"].lower()

    exported = client.post(f"/api/payments/batches/{batch.json()['id']}/export", headers=admin_headers)
    assert exported.status_code == 200, exported.text
    failed = client.post(
        f"/api/payments/{payment_id}/mark-failed",
        headers=admin_headers,
        json={"failure_reason": "Processor returned a temporary rejection"},
    )
    assert failed.status_code == 200, failed.text
    assert failed.json()["status"] == "failed"
    assert failed.json()["failure_reason"] == "Processor returned a temporary rejection"
    assert failed.json()["history"][-1]["event_type"] == "failed"

    payment = db.get(PaymentRecord, UUID(payment_id))
    assert payment is not None
    foreign_org = Organization(name="Other tenant", code="OTHER")
    db.add(foreign_org)
    db.flush()
    foreign_department = Department(organization_id=foreign_org.id, code="OPS", name="Operations")
    db.add(foreign_department)
    db.flush()
    foreign_user = User(
        organization_id=foreign_org.id,
        department_id=foreign_department.id,
        employee_number="OTHER-001",
        username="other.employee",
        email="other.employee@example.com",
        password_hash="not-used",
        full_name="Other Employee",
        status="active",
    )
    db.add(foreign_user)
    db.flush()
    foreign_report = ExpenseReport(
        report_number="RPT-OTHER-PAYMENT",
        employee_user_id=foreign_user.id,
        department_id=foreign_department.id,
        title="Other tenant report",
        currency_code="USD",
        status="approved_pending_payment",
        total_amount=50,
    )
    db.add(foreign_report)
    db.flush()
    foreign_payment = PaymentRecord(
        expense_report_id=foreign_report.id,
        payment_reference="PAY-RPT-OTHER-PAYMENT",
        amount=50,
        status="pending",
    )
    db.add(foreign_payment)
    db.commit()

    visible = client.get("/api/payments", headers=admin_headers)
    assert visible.status_code == 200, visible.text
    assert {entry["id"] for entry in visible.json()["items"]} == {payment_id}

    own_report = db.get(ExpenseReport, payment.expense_report_id)
    assert own_report is not None
    own_employee = db.get(User, own_report.employee_user_id)
    assert own_employee is not None
    with pytest.raises(payment_service.PaymentNotFoundError):
        payment_service.get_payment(db, foreign_payment.id, own_employee.organization_id)
