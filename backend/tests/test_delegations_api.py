"""Approvers can manage only their own temporary approval delegation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


PASSWORD = "correct-horse-battery-staple"


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login(client, email: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return _headers(response.json()["access_token"])


def test_approver_can_create_list_and_deactivate_their_own_delegation(client):
    bootstrap = client.post(
        "/api/auth/bootstrap",
        json={"full_name": "Admin", "email": "delegations-admin@example.com", "password": PASSWORD},
    )
    assert bootstrap.status_code == 201, bootstrap.text
    admin_headers = _headers(bootstrap.json()["access_token"])
    manager = client.post(
        "/api/users",
        headers=admin_headers,
        json={
            "full_name": "Morgan Manager",
            "email": "delegations-manager@example.com",
            "password": PASSWORD,
            "roles": ["employee", "approver"],
        },
    )
    assert manager.status_code == 201, manager.text
    delegate = client.post(
        "/api/users",
        headers=admin_headers,
        json={
            "full_name": "Devon Delegate",
            "email": "delegations-delegate@example.com",
            "password": PASSWORD,
            "roles": ["employee", "approver"],
        },
    )
    assert delegate.status_code == 201, delegate.text

    now = datetime.now(UTC)
    manager_headers = _login(client, "delegations-manager@example.com")
    candidates = client.get("/api/delegations/candidates", headers=manager_headers)
    assert candidates.status_code == 200, candidates.text
    assert {entry["id"] for entry in candidates.json()} >= {delegate.json()["id"]}
    created = client.post(
        "/api/delegations",
        headers=manager_headers,
        json={
            "delegate_user_id": delegate.json()["id"],
            "start_date": (now - timedelta(hours=1)).isoformat(),
            "end_date": (now + timedelta(days=2)).isoformat(),
            "scope": "approval",
            "remarks": "Out of office",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["delegator_user_id"] == manager.json()["id"]
    assert created.json()["delegate_user_id"] == delegate.json()["id"]
    assert created.json()["is_active"] is True

    listed = client.get("/api/delegations", headers=manager_headers)
    assert listed.status_code == 200, listed.text
    assert [entry["id"] for entry in listed.json()] == [created.json()["id"]]

    deactivated = client.delete(f"/api/delegations/{created.json()['id']}", headers=manager_headers)
    assert deactivated.status_code == 200, deactivated.text
    assert deactivated.json()["is_active"] is False
    assert client.get("/api/delegations", headers=manager_headers).json() == []
