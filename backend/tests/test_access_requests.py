"""Regression tests for access-request administration routes."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.api.routes import access_requests
from app.models.user_access_request import UserAccessRequest
from app.services import access_request_service, user_service


def test_approve_request_uses_authenticated_user_id(monkeypatch, db) -> None:
    admin_id = uuid.uuid4()
    organization_id = uuid.uuid4()
    request_id = uuid.uuid4()
    department_id = uuid.uuid4()
    created_user_id = uuid.uuid4()
    captured: dict[str, object] = {}

    def approve(_db, received_request_id, received_admin_id, received_organization_id, received_department_id):
        captured.update(
            request_id=received_request_id,
            admin_id=received_admin_id,
            organization_id=received_organization_id,
            department_id=received_department_id,
        )
        return SimpleNamespace(id=created_user_id)

    monkeypatch.setattr(access_requests.access_request_service, "approve_request", approve)

    response = access_requests.approve_request(
        request_id,
        access_requests.AccessRequestApprove(department_id=department_id),
        db,
        {"user_id": str(admin_id), "organization_id": str(organization_id)},
    )

    assert response == {"message": "Access approved", "user_id": str(created_user_id)}
    assert captured == {
        "request_id": request_id,
        "admin_id": admin_id,
        "organization_id": organization_id,
        "department_id": department_id,
    }


def test_reject_request_uses_authenticated_user_id(monkeypatch, db) -> None:
    admin_id = uuid.uuid4()
    request_id = uuid.uuid4()
    captured: dict[str, object] = {}

    organization_id = uuid.uuid4()

    def reject(_db, received_request_id, received_admin_id, received_organization_id):
        captured.update(
            request_id=received_request_id,
            admin_id=received_admin_id,
            organization_id=received_organization_id,
        )
        return SimpleNamespace(id=request_id)

    monkeypatch.setattr(access_requests.access_request_service, "reject_request", reject)

    response = access_requests.reject_request(
        request_id,
        db,
        {"user_id": str(admin_id), "organization_id": str(organization_id)},
    )

    assert response == {"message": "Access rejected", "request_id": str(request_id)}
    assert captured == {"request_id": request_id, "admin_id": admin_id, "organization_id": organization_id}


def test_create_request_uses_configured_default_organization(db, seeded_org) -> None:
    request = access_request_service.create_access_request(
        db,
        email="new.employee@example.com",
        full_name="New Employee",
    )

    assert request.organization_id == seeded_org.id


def test_approved_request_becomes_an_employee(db, seeded_org, seeded_department, seeded_user) -> None:
    request = access_request_service.create_access_request(
        db,
        email="approved.employee@example.com",
        full_name="Approved Employee",
    )

    approved_user = access_request_service.approve_request(
        db,
        request.id,
        seeded_user.id,
        seeded_org.id,
        seeded_department.id,
    )

    stored_request = db.get(UserAccessRequest, request.id)
    assert stored_request is not None
    assert stored_request.status == "approved"
    assert stored_request.user_id == approved_user.id
    assert user_service.role_codes_for_user(db, approved_user.id) == ["employee"]
