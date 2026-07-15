"""High-value API path: bootstrap → policy → report → approval → notification."""

from __future__ import annotations

from datetime import UTC, datetime


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login(client, email: str) -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 200, response.text
    return _headers(response.json()["access_token"])


def test_full_reimbursement_flow(client):
    bootstrap = client.post(
        "/api/auth/bootstrap",
        json={
            "organization_name": "End-to-end Co",
            "organization_code": "E2E",
            "department_name": "Engineering",
            "department_code": "ENG",
            "full_name": "Avery Admin",
            "email": "admin@example.com",
            "password": "correct-horse-battery-staple",
        },
    )
    assert bootstrap.status_code == 201, bootstrap.text
    admin_headers = _headers(bootstrap.json()["access_token"])

    manager = client.post(
        "/api/users",
        headers=admin_headers,
        json={
            "full_name": "Morgan Manager",
            "email": "manager@example.com",
            "password": "correct-horse-battery-staple",
            "roles": ["employee", "approver"],
        },
    )
    assert manager.status_code == 201, manager.text
    employee = client.post(
        "/api/users",
        headers=admin_headers,
        json={
            "full_name": "Elliot Employee",
            "email": "employee@example.com",
            "password": "correct-horse-battery-staple",
            "roles": ["employee"],
            "manager_id": manager.json()["id"],
        },
    )
    assert employee.status_code == 201, employee.text

    category = client.post(
        "/api/categories",
        headers=admin_headers,
        json={"code": "TRAVEL", "name": "Travel", "receipt_required": True},
    )
    assert category.status_code == 201, category.text
    policy = client.post(
        "/api/policies",
        headers=admin_headers,
        json={
            "name": "Travel policy",
            "version_label": "v1",
            "effective_from": datetime.now(UTC).isoformat(),
            "rules": [{"category_id": category.json()["id"], "max_per_trip": 200}],
        },
    )
    assert policy.status_code == 201, policy.text
    activated = client.post(f"/api/policies/{policy.json()['id']}/activate", headers=admin_headers)
    assert activated.status_code == 200, activated.text

    employee_headers = _login(client, "employee@example.com")
    assert client.get("/api/categories", headers=employee_headers).status_code == 200
    assert client.get("/api/vendors", headers=employee_headers).status_code == 200

    report = client.post(
        "/api/reports",
        headers=employee_headers,
        json={"title": "Client visit", "description": "July onsite", "currency": "USD"},
    )
    assert report.status_code == 201, report.text
    report_id = report.json()["id"]
    item = client.post(
        f"/api/reports/{report_id}/items",
        headers=employee_headers,
        json={
            "category_id": category.json()["id"],
            "amount": "125.00",
            "currency": "USD",
            "description": "Train to client",
            "expense_date": "2026-07-15",
        },
    )
    assert item.status_code == 201, item.text
    assert item.json()["category_name"] == "Travel"

    submitted = client.post(f"/api/reports/{report_id}/submit", headers=employee_headers)
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "submitted"
    assert submitted.json()["approval_history"][0]["action"] == "submitted"

    manager_headers = _login(client, "manager@example.com")
    queue = client.get("/api/approvals/queue", headers=manager_headers)
    assert queue.status_code == 200, queue.text
    assert [entry["id"] for entry in queue.json()] == [report_id]

    internal = client.post(
        f"/api/reports/{report_id}/comments",
        headers=manager_headers,
        json={"body": "Internal review note", "visibility": "internal"},
    )
    assert internal.status_code == 201, internal.text
    employee_comments = client.get(f"/api/reports/{report_id}/comments", headers=employee_headers)
    assert employee_comments.status_code == 200
    assert employee_comments.json() == []

    employee_visible = client.post(
        f"/api/reports/{report_id}/comments",
        headers=manager_headers,
        json={"body": "Looks good", "visibility": "employee"},
    )
    assert employee_visible.status_code == 201, employee_visible.text
    assert [comment["body"] for comment in client.get(f"/api/reports/{report_id}/comments", headers=employee_headers).json()] == ["Looks good"]

    approved = client.post(f"/api/approvals/{report_id}/approve", headers=manager_headers, json={"remarks": "Approved"})
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved_pending_payment"
    assert approved.json()["approval_history"][-1]["action"] == "approve"
    history = client.get("/api/approvals/history", headers=manager_headers)
    assert history.status_code == 200, history.text
    assert history.json()[0]["id"] == report_id
    assert history.json()[0]["approval_status"] == "approved"

    notifications = client.get("/api/notifications", headers=employee_headers)
    assert notifications.status_code == 200, notifications.text
    assert notifications.json()[0]["report_id"] == report_id
    marked_read = client.post(f"/api/notifications/{notifications.json()[0]['id']}/read", headers=employee_headers)
    assert marked_read.status_code == 200
    assert marked_read.json()["read_at"] is not None


def test_policy_violation_blocks_submission_without_changing_draft(client):
    bootstrap = client.post(
        "/api/auth/bootstrap",
        json={
            "full_name": "Admin",
            "email": "admin@example.com",
            "password": "correct-horse-battery-staple",
        },
    )
    admin_headers = _headers(bootstrap.json()["access_token"])
    manager = client.post(
        "/api/users",
        headers=admin_headers,
        json={"full_name": "Manager", "email": "manager@example.com", "password": "correct-horse-battery-staple", "roles": ["approver"]},
    )
    employee = client.post(
        "/api/users",
        headers=admin_headers,
        json={
            "full_name": "Employee",
            "email": "employee@example.com",
            "password": "correct-horse-battery-staple",
            "roles": ["employee"],
            "manager_id": manager.json()["id"],
        },
    )
    assert employee.status_code == 201, employee.text
    category = client.post("/api/categories", headers=admin_headers, json={"code": "MEALS", "name": "Meals"})
    policy = client.post(
        "/api/policies",
        headers=admin_headers,
        json={
            "name": "Meal policy",
            "version_label": "v1",
            "effective_from": datetime.now(UTC).isoformat(),
            "rules": [{"category_id": category.json()["id"], "max_per_trip": 20}],
        },
    )
    assert client.post(f"/api/policies/{policy.json()['id']}/activate", headers=admin_headers).status_code == 200
    employee_headers = _login(client, "employee@example.com")
    report = client.post("/api/reports", headers=employee_headers, json={"title": "Lunch"})
    report_id = report.json()["id"]
    assert client.post(
        f"/api/reports/{report_id}/items",
        headers=employee_headers,
        json={
            "category_id": category.json()["id"],
            "amount": 50,
            "description": "Customer lunch",
            "expense_date": "2026-07-15",
        },
    ).status_code == 201

    blocked = client.post(f"/api/reports/{report_id}/submit", headers=employee_headers)
    assert blocked.status_code == 422, blocked.text
    assert "violations" in blocked.json()["detail"]
    report_after = client.get(f"/api/reports/{report_id}", headers=employee_headers)
    assert report_after.json()["status"] == "draft"
    assert report_after.json()["line_items"][0]["is_policy_violated"] is True
