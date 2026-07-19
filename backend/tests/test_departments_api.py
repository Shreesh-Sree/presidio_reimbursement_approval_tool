"""Regression coverage for the access-request department lookup API."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.routes import departments
from app.core.database import get_db
from app.models.department import Department
from app.models.organization import Organization


def _client_for_departments(engine, seeded_user):
    app = FastAPI()
    app.include_router(departments.router)

    def override_db():
        session = Session(engine)
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    for route in departments.router.routes:
        for dependency in route.dependant.dependencies:
            if dependency.call is not get_db:
                app.dependency_overrides[dependency.call] = lambda: {
                    "organization_id": str(seeded_user.organization_id),
                    "user_id": str(seeded_user.id),
                }
    return TestClient(app)


def test_departments_lookup_returns_only_active_departments_in_current_organization(
    engine, db, seeded_department, seeded_org, seeded_user
) -> None:
    accounts = Department(organization_id=seeded_org.id, code="ACC", name="Accounts")
    inactive = Department(
        organization_id=seeded_org.id,
        code="OLD",
        name="Former Department",
        status="inactive",
    )
    deleted = Department(
        organization_id=seeded_org.id,
        code="DEL",
        name="Deleted Department",
        is_deleted=True,
        deleted_at=datetime.now(UTC),
    )
    other_organization = Organization(name="Other Organization", code="OTHER", base_currency="USD")
    db.add_all([accounts, inactive, deleted, other_organization])
    db.flush()
    other_department = Department(
        organization_id=other_organization.id,
        code="OPS",
        name="Other Operations",
    )
    db.add(other_department)
    db.commit()

    with _client_for_departments(engine, seeded_user) as client:
        response = client.get("/api/departments")

    assert response.status_code == 200, response.text
    assert response.json() == [
        {
            "id": str(accounts.id),
            "code": "ACC",
            "name": "Accounts",
            "status": "active",
            "department_head_user_id": None,
        },
        {
            "id": str(seeded_department.id),
            "code": "ENG",
            "name": "Engineering",
            "status": "active",
            "department_head_user_id": None,
        },
    ]


def test_department_management_is_tenant_scoped_and_preserves_active_assignments(
    engine, db, seeded_department, seeded_org, seeded_user
) -> None:
    other_organization = Organization(name="Other Organization", code="OTHER", base_currency="USD")
    db.add(other_organization)
    db.flush()
    other_department = Department(organization_id=other_organization.id, code="OPS", name="Other Operations")
    db.add(other_department)
    db.commit()

    with _client_for_departments(engine, seeded_user) as client:
        created = client.post("/api/departments", json={"code": " fin ", "name": "Finance"})
        assert created.status_code == 201, created.text
        finance = created.json()
        assert finance == {
            "id": finance["id"],
            "code": "FIN",
            "name": "Finance",
            "status": "active",
            "department_head_user_id": None,
        }

        duplicate = client.post("/api/departments", json={"code": "fin", "name": "Duplicate"})
        assert duplicate.status_code == 409
        assert duplicate.json()["detail"] == "A department with that code already exists"

        inactive = client.patch(f"/api/departments/{finance['id']}", json={"status": "inactive"})
        assert inactive.status_code == 200, inactive.text
        assert inactive.json()["status"] == "inactive"

        listed = client.get("/api/departments?include_inactive=true")
        assert listed.status_code == 200
        assert {department["code"] for department in listed.json()} == {"ENG", "FIN"}

        protected = client.patch(f"/api/departments/{seeded_department.id}", json={"status": "inactive"})
        assert protected.status_code == 409
        assert protected.json()["detail"] == "Reassign active employees before deactivating this department"

        foreign = client.patch(f"/api/departments/{other_department.id}", json={"name": "Nope"})
        assert foreign.status_code == 404
