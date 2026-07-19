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
        {"id": str(accounts.id), "name": "Accounts"},
        {"id": str(seeded_department.id), "name": "Engineering"},
    ]
