"""Workflow-rule administration API coverage."""

from __future__ import annotations


def _bootstrap(client):
    response = client.post(
        "/api/auth/bootstrap",
        json={
            "organization_name": "Acme Reimbursement",
            "organization_code": "ACME",
            "department_name": "Finance",
            "department_code": "FIN",
            "full_name": "Ada Admin",
            "email": "ada.admin@example.com",
            "password": "correct-horse-battery-staple",
        },
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    return {"Authorization": f"Bearer {payload['access_token']}"}


def _create_user(client, headers, *, full_name, email, roles):
    response = client.post(
        "/api/users",
        headers=headers,
        json={
            "full_name": full_name,
            "email": email,
            "password": "correct-horse-battery-staple",
            "roles": roles,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_workflow_rules_can_be_created_updated_listed_and_deleted(client):
    headers = _bootstrap(client)
    named_approver = _create_user(
        client,
        headers,
        full_name="Morgan Manager",
        email="morgan.manager@example.com",
        roles=["employee", "approver"],
    )

    created = client.post(
        "/api/workflows",
        headers=headers,
        json={
            "name": "Large travel escalation",
            "conditions": {"min_total": "1000.00", "max_total": "5000.00", "currency_code": "usd"},
            "approval_chain": [
                {"manager_level": 1},
                {"user_id": named_approver["id"]},
                {"role_code": "approver"},
            ],
            "priority": 20,
        },
    )
    assert created.status_code == 201, created.text
    rule = created.json()
    assert rule["conditions"] == {"min_total": 1000.0, "max_total": 5000.0, "currency_code": "USD"}
    assert rule["approval_chain"] == [
        {"manager_level": 1},
        {"user_id": named_approver["id"]},
        {"role_code": "approver"},
    ]
    assert "organization_id" not in rule["conditions"]

    listed = client.get("/api/workflows", headers=headers)
    assert listed.status_code == 200
    assert [entry["id"] for entry in listed.json()] == [rule["id"]]

    updated = client.patch(
        f"/api/workflows/{rule['id']}",
        headers=headers,
        json={"priority": 5, "is_active": False},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["priority"] == 5
    assert updated.json()["is_active"] is False

    fetched = client.get(f"/api/workflows/{rule['id']}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Large travel escalation"

    deleted = client.delete(f"/api/workflows/{rule['id']}", headers=headers)
    assert deleted.status_code == 204, deleted.text
    assert client.get("/api/workflows", headers=headers).json() == []


def test_workflow_rules_require_permission_and_valid_approver_chain(client):
    headers = _bootstrap(client)
    employee = _create_user(
        client,
        headers,
        full_name="Erin Employee",
        email="erin.employee@example.com",
        roles=["employee"],
    )
    login = client.post(
        "/api/auth/login",
        json={"email": "erin.employee@example.com", "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200
    employee_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    denied = client.get("/api/workflows", headers=employee_headers)
    assert denied.status_code == 403
    assert denied.json()["detail"] == "Missing permission: workflow:manage"

    invalid_thresholds = client.post(
        "/api/workflows",
        headers=headers,
        json={
            "name": "Invalid thresholds",
            "conditions": {"min_total": 100, "max_total": 50},
            "approval_chain": [{"manager_level": 1}],
        },
    )
    assert invalid_thresholds.status_code == 422

    invalid_user = client.post(
        "/api/workflows",
        headers=headers,
        json={
            "name": "Employee cannot approve",
            "approval_chain": [{"user_id": employee["id"]}],
        },
    )
    assert invalid_user.status_code == 422
    assert invalid_user.json()["detail"] == "Configured user must have report approval permission"

    invalid_selector = client.post(
        "/api/workflows",
        headers=headers,
        json={
            "name": "Ambiguous step",
            "approval_chain": [{"manager_level": 1, "role_code": "approver"}],
        },
    )
    assert invalid_selector.status_code == 422
