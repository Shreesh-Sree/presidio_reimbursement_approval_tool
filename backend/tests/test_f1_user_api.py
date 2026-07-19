"""F1 API coverage: bootstrap, RBAC, users, managers, and organization tree."""

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
    return payload, {"Authorization": f"Bearer {payload['access_token']}"}


def test_bootstrap_user_lifecycle_and_org_chart(client):
    bootstrap, headers = _bootstrap(client)
    assert bootstrap["user"]["roles"] == ["administrator"]
    assert "user:create" in bootstrap["user"]["permissions"]

    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "ada.admin@example.com"

    roles = client.get("/api/roles", headers=headers)
    assert roles.status_code == 200
    assert {role["code"] for role in roles.json()} == {"administrator", "approver", "employee", "finance"}

    operations = client.post(
        "/api/departments",
        headers=headers,
        json={"code": "OPS", "name": "Operations"},
    )
    assert operations.status_code == 201, operations.text
    operations_payload = operations.json()

    manager = client.post(
        "/api/users",
        headers=headers,
        json={
            "full_name": "Manny Manager",
            "email": "manny.manager@example.com",
            "password": "correct-horse-battery-staple",
            "roles": ["employee", "approver"],
        },
    )
    assert manager.status_code == 201, manager.text
    manager_payload = manager.json()
    assert set(manager_payload["roles"]) == {"employee", "approver"}
    assert manager_payload["organization_name"] == "Acme Reimbursement"
    assert manager_payload["department_name"] == "Finance"

    finance = client.post(
        "/api/users",
        headers=headers,
        json={
            "full_name": "Fiona Finance",
            "email": "fiona.finance@example.com",
            "password": "correct-horse-battery-staple",
            "roles": ["finance"],
        },
    )
    assert finance.status_code == 201, finance.text
    assert finance.json()["roles"] == ["finance"]

    employee = client.post(
        "/api/users",
        headers=headers,
        json={
            "full_name": "Eli Employee",
            "email": "eli.employee@example.com",
            "password": "correct-horse-battery-staple",
            "roles": ["employee"],
            "manager_id": manager_payload["id"],
            "department_id": operations_payload["id"],
        },
    )
    assert employee.status_code == 201, employee.text
    employee_payload = employee.json()
    assert employee_payload["manager_id"] == manager_payload["id"]
    assert employee_payload["manager_name"] == "Manny Manager"
    assert employee_payload["department_id"] == operations_payload["id"]
    assert employee_payload["department_name"] == "Operations"

    invalid_manager = client.post(
        "/api/users",
        headers=headers,
        json={
            "full_name": "No Manager",
            "email": "no.manager@example.com",
            "password": "correct-horse-battery-staple",
            "roles": ["employee"],
            "manager_id": employee_payload["id"],
        },
    )
    assert invalid_manager.status_code == 400
    assert invalid_manager.json()["detail"] == "Reporting manager must have the approver role"

    updated = client.patch(
        f"/api/users/{employee_payload['id']}",
        headers=headers,
        json={
            "full_name": "Eli Updated",
            "email": "eli.employee@example.com",
            "roles": ["employee"],
            "manager_id": manager_payload["id"],
            "department_id": bootstrap["user"]["department_id"],
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["full_name"] == "Eli Updated"
    assert updated.json()["department_name"] == "Finance"

    tree = client.get("/api/org-chart", headers=headers)
    assert tree.status_code == 200, tree.text
    nodes = tree.json()
    manager_node = next(node for node in nodes if node["id"] == manager_payload["id"])
    assert [report["id"] for report in manager_node["reports"]] == [employee_payload["id"]]

    deactivated = client.post(f"/api/users/{employee_payload['id']}/deactivate", headers=headers)
    assert deactivated.status_code == 200, deactivated.text
    assert deactivated.json()["status"] == "inactive"

    logout = client.post("/api/auth/logout", headers=headers)
    assert logout.status_code == 200
    assert client.get("/api/auth/me", headers=headers).status_code == 401
    assert client.post("/api/auth/bootstrap", json={
        "full_name": "Other Admin",
        "email": "other@example.com",
        "password": "correct-horse-battery-staple",
    }).status_code == 409


def test_employee_cannot_access_user_administration(client):
    _, admin_headers = _bootstrap(client)
    created = client.post(
        "/api/users",
        headers=admin_headers,
        json={
            "full_name": "Erin Employee",
            "email": "erin.employee@example.com",
            "password": "correct-horse-battery-staple",
            "roles": ["employee"],
        },
    )
    assert created.status_code == 201, created.text

    login = client.post(
        "/api/auth/login",
        json={"email": "erin.employee@example.com", "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200, login.text
    employee_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    denied = client.get("/api/users", headers=employee_headers)
    assert denied.status_code == 403
    assert denied.json()["detail"] == "Missing permission: user:read"
