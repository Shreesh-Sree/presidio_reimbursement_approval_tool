"""Cross-tenant attachment authorization regressions."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.routes import attachments
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.attachment import Attachment
from app.models.department import Department
from app.models.organization import Organization
from app.models.policy import Policy
from app.models.user import User


def test_policy_document_download_rejects_another_tenant_policy_manager(
    engine, db, seeded_org, seeded_user
) -> None:
    policy = Policy(
        organization_id=seeded_org.id,
        name="Private travel policy",
        version_label="v1",
        is_active=True,
        effective_from=datetime.now(UTC),
    )
    db.add(policy)
    db.flush()
    attachment = Attachment(
        entity_type="policy_document",
        entity_id=policy.id,
        file_name="private.pdf",
        original_file_name="private.pdf",
        storage_path="local://policies/private.pdf",
        mime_type="application/pdf",
        file_size_bytes=12,
        checksum="a" * 64,
        uploaded_by=seeded_user.id,
    )
    db.add(attachment)
    db.flush()
    policy.uploaded_document_attachment_id = attachment.id

    other_org = Organization(name="Other tenant", code="OTHER-DOWNLOAD")
    db.add(other_org)
    db.flush()
    other_department = Department(organization_id=other_org.id, code="OPS", name="Operations")
    db.add(other_department)
    db.flush()
    actor = User(
        organization_id=other_org.id,
        department_id=other_department.id,
        employee_number="OTHER-1",
        username="other-manager",
        email="other-manager@example.com",
        password_hash="unused",
        full_name="Other Manager",
        status="active",
    )
    db.add(actor)
    db.commit()

    app = FastAPI()
    app.include_router(attachments.router)

    def override_db():
        session = Session(engine)
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": str(actor.id),
        "organization_id": str(other_org.id),
        "permissions": ["policy:manage"],
    }
    with TestClient(app) as client:
        response = client.get(f"/api/attachments/{attachment.id}/download")

    assert response.status_code == 403
