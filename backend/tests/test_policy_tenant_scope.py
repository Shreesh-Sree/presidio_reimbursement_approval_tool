"""Regression coverage for organization-scoped policy ownership."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.routes import policies
from app.core.database import get_db
from app.core.security import hash_password
from app.models.department import Department
from app.models.organization import Organization
from app.models.user import User
from app.services import policy_assistant_client, policy_service


def _policy_client(engine, actor: User) -> TestClient:
    app = FastAPI()
    app.include_router(policies.router)

    def override_db():
        session = Session(engine)
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    actor_payload = {
        "user_id": str(actor.id),
        "email": actor.email,
        "organization_id": str(actor.organization_id),
    }
    for route in policies.router.routes:
        for dependency in route.dependant.dependencies:
            if dependency.call is not get_db:
                app.dependency_overrides[dependency.call] = lambda payload=actor_payload: payload
    return TestClient(app)


def _other_tenant_admin(db: Session) -> tuple[Organization, User]:
    organization = Organization(name="Other Tenant", code="OTHER", base_currency="USD")
    db.add(organization)
    db.flush()
    department = Department(organization_id=organization.id, code="OPS", name="Operations")
    db.add(department)
    db.flush()
    user = User(
        organization_id=organization.id,
        department_id=department.id,
        employee_number="OTHER-ADMIN",
        username="other-admin",
        email="other-admin@example.com",
        password_hash=hash_password("correct-horse-battery-staple"),
        full_name="Other Tenant Admin",
        status="active",
    )
    db.add(user)
    db.commit()
    return organization, user


def test_policy_service_is_tenant_scoped_and_activation_does_not_cross_tenants(db, seeded_org):
    other_org, _ = _other_tenant_admin(db)
    effective_from = datetime.now(UTC)
    policy_a = policy_service.create_policy_version(
        db,
        "Travel",
        "v1",
        effective_from,
        organization_id=seeded_org.id,
    )
    policy_b = policy_service.create_policy_version(
        db,
        "Travel",
        "v1",
        effective_from,
        organization_id=other_org.id,
    )

    policy_service.activate_policy(db, policy_a.id, organization_id=seeded_org.id)
    policy_service.activate_policy(db, policy_b.id, organization_id=other_org.id)

    assert [policy.id for policy in policy_service.list_policies(db, seeded_org.id)] == [policy_a.id]
    assert [policy.id for policy in policy_service.list_policies(db, other_org.id)] == [policy_b.id]
    assert policy_service.get_active_policy(db, seeded_org.id).id == policy_a.id
    assert policy_service.get_active_policy(db, other_org.id).id == policy_b.id
    with pytest.raises(policy_service.PolicyNotFoundError):
        policy_service.get_policy(db, policy_a.id, other_org.id)


def test_policy_routes_hide_cross_tenant_policy_and_do_not_call_assistant(
    engine,
    db,
    seeded_org,
    monkeypatch,
):
    other_org, other_admin = _other_tenant_admin(db)
    policy = policy_service.create_policy_version(
        db,
        "Travel",
        "v1",
        datetime.now(UTC),
        organization_id=seeded_org.id,
        rules_data=[{"category_name": "Travel", "max_per_trip": "500"}],
    )
    monkeypatch.setattr(
        policy_assistant_client,
        "index_policy_text",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("cross-tenant assistant index must not run")),
    )
    monkeypatch.setattr(
        policy_assistant_client,
        "ask_policy",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("cross-tenant assistant query must not run")),
    )

    with _policy_client(engine, other_admin) as client:
        listed = client.get("/api/policies")
        assert listed.status_code == 200
        assert listed.json() == []

        # The same name/version is legal in a separate tenant, and carries
        # only that tenant's rule set.
        created = client.post(
            "/api/policies",
            json={
                "name": "Travel",
                "version_label": "v1",
                "effective_from": datetime.now(UTC).isoformat(),
                "rules": [{"category_name": "Meals", "max_per_trip": 40}],
            },
        )
        assert created.status_code == 201, created.text
        assert created.json()["organization_id"] == str(other_org.id)
        assert created.json()["rules"][0]["category_name"] == "Meals"

        assert client.get(f"/api/policies/{policy.id}").status_code == 404
        assert client.patch(f"/api/policies/{policy.id}", json={"name": "Leaked"}).status_code == 404
        assert client.post(f"/api/policies/{policy.id}/activate").status_code == 404
        assert client.post(
            f"/api/policies/{policy.id}/upload-doc",
            files={"file": ("policy.pdf", b"%PDF-cross-tenant", "application/pdf")},
        ).status_code == 404
        assert client.post(
            f"/api/policies/{policy.id}/assistant-index",
            json={"content": "Policy content must remain tenant scoped."},
        ).status_code == 404
        assert client.post(
            f"/api/policies/{policy.id}/assistant-ask",
            json={"question": "What is the limit?"},
        ).status_code == 404
