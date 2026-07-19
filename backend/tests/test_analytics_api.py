"""Role-scoped, aggregate analytics API coverage."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from app.models.expense_category import ExpenseCategory
from app.models.expense_item import ExpenseItem
from app.models.expense_report import ExpenseReport
from app.models.user import User


PASSWORD = "correct-horse-battery-staple"


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login(client, email: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return _headers(response.json()["access_token"])


def test_overview_is_aggregate_and_scoped_to_the_authenticated_user(client, db):
    bootstrap = client.post(
        "/api/auth/bootstrap",
        json={
            "organization_name": "Analytics Co",
            "organization_code": "ANALYTICS",
            "department_name": "Engineering",
            "department_code": "ENG",
            "full_name": "Ada Admin",
            "email": "analytics-admin@example.com",
            "password": PASSWORD,
        },
    )
    assert bootstrap.status_code == 201, bootstrap.text
    admin_headers = _headers(bootstrap.json()["access_token"])

    employee = client.post(
        "/api/users",
        headers=admin_headers,
        json={
            "full_name": "Erin Employee",
            "email": "analytics-employee@example.com",
            "password": PASSWORD,
            "roles": ["employee"],
        },
    )
    assert employee.status_code == 201, employee.text
    other_employee = client.post(
        "/api/users",
        headers=admin_headers,
        json={
            "full_name": "Owen Other",
            "email": "analytics-other@example.com",
            "password": PASSWORD,
            "roles": ["employee"],
        },
    )
    assert other_employee.status_code == 201, other_employee.text

    category = ExpenseCategory(
        organization_id=UUID(bootstrap.json()["user"]["organization_id"]),
        code="TRAVEL",
        name="Travel",
    )
    db.add(category)
    db.flush()
    employee_model = db.get(User, UUID(employee.json()["id"]))
    other_model = db.get(User, UUID(other_employee.json()["id"]))
    assert employee_model is not None and other_model is not None

    today = datetime.now(UTC)
    own_report = ExpenseReport(
        report_number="RPT-ANALYTICS-OWN",
        employee_user_id=employee_model.id,
        department_id=employee_model.department_id,
        title="Own client travel",
        currency_code="USD",
        status="approved_pending_payment",
        total_amount=Decimal("120.00"),
        submitted_at=today - timedelta(days=4),
    )
    other_report = ExpenseReport(
        report_number="RPT-ANALYTICS-OTHER",
        employee_user_id=other_model.id,
        department_id=other_model.department_id,
        title="Other client travel",
        currency_code="USD",
        status="rejected",
        total_amount=Decimal("80.00"),
        submitted_at=today - timedelta(days=3),
    )
    db.add_all([own_report, other_report])
    db.flush()
    db.add_all(
        [
            ExpenseItem(
                expense_report_id=own_report.id,
                line_number=1,
                category_id=category.id,
                amount=Decimal("120.00"),
                original_amount=Decimal("120.00"),
                currency_code="USD",
                expense_date=today.date(),
                is_policy_violated=True,
                policy_violation_reason="Needs a receipt",
            ),
            ExpenseItem(
                expense_report_id=other_report.id,
                line_number=1,
                category_id=category.id,
                amount=Decimal("80.00"),
                original_amount=Decimal("80.00"),
                currency_code="USD",
                expense_date=today.date(),
            ),
        ]
    )
    db.commit()

    admin_overview = client.get("/api/analytics/overview", headers=admin_headers)
    assert admin_overview.status_code == 200, admin_overview.text
    assert admin_overview.json()["scope"] == "organization"
    assert admin_overview.json()["summary"]["report_count"] == 2
    assert admin_overview.json()["summary"]["policy_violation_count"] == 1
    assert admin_overview.json()["spending_by_category"] == [
        {"category": "Travel", "amount": 200.0, "currency": "USD"}
    ]
    assert "Erin Employee" not in admin_overview.text
    assert "analytics-employee@example.com" not in admin_overview.text

    employee_overview = client.get(
        "/api/analytics/overview",
        headers=_login(client, "analytics-employee@example.com"),
    )
    assert employee_overview.status_code == 200, employee_overview.text
    assert employee_overview.json()["scope"] == "personal"
    assert employee_overview.json()["summary"]["report_count"] == 1
    assert employee_overview.json()["spending_by_category"] == [
        {"category": "Travel", "amount": 120.0, "currency": "USD"}
    ]
