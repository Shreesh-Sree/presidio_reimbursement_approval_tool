from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.routes import categories, policies
from app.core.database import get_db


def _client_for_routes(engine, seeded_user):
    app = FastAPI()
    app.include_router(policies.router)
    app.include_router(categories.router)

    def override_db():
        session = Session(engine)
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    # The route's permission dependency is a closure produced by
    # require_permission.  Override each closure so this contract test focuses
    # on API parsing/serialization rather than role fixture setup.
    for route in [*policies.router.routes, *categories.router.routes]:
        for dependency in route.dependant.dependencies:
            if dependency.call is not get_db:
                app.dependency_overrides[dependency.call] = lambda: {
                "user_id": str(seeded_user.id),
                "email": seeded_user.email,
                "organization_id": str(seeded_user.organization_id),
                }
    return TestClient(app)


def test_policy_routes_create_upload_and_activate(engine, db, seeded_user, tmp_path, monkeypatch):
    db.commit()
    monkeypatch.setenv("LOCAL_STORAGE_PATH", str(tmp_path / "uploads"))
    with _client_for_routes(engine, seeded_user) as client:
        created = client.post(
            "/api/policies",
            json={
                "name": "Travel policy",
                "version_label": "v1",
                "effective_from": "2026-01-01",
                "effective_to": "2026-12-31",
                "rules": [
                    {
                        "category_name": "Travel",
                        "per_category_cap": 500,
                        "receipt_required_above": 25,
                    }
                ],
            },
        )
        assert created.status_code == 201, created.text
        policy = created.json()
        assert policy["status"] == "draft"
        assert policy["rules"][0]["category_name"] == "Travel"

        uploaded = client.post(
            f"/api/policies/{policy['id']}/upload-doc",
            files={"file": ("travel.pdf", b"%PDF-policy", "application/pdf")},
        )
        assert uploaded.status_code == 200, uploaded.text
        assert uploaded.json()["document_url"].startswith("/api/attachments/")

        activated = client.post(f"/api/policies/{policy['id']}/activate")
        assert activated.status_code == 200
        assert activated.json()["status"] == "active"


def test_category_routes_create_hierarchy_update_and_delete(engine, db, seeded_user):
    db.commit()
    with _client_for_routes(engine, seeded_user) as client:
        parent = client.post("/api/categories", json={"code": "TRAVEL", "name": "Travel"})
        assert parent.status_code == 201, parent.text
        child = client.post(
            "/api/categories",
            json={"code": "AIR", "name": "Airfare", "parent_id": parent.json()["id"]},
        )
        assert child.status_code == 201, child.text

        listed = client.get("/api/categories")
        assert listed.status_code == 200
        assert listed.json()[0]["children"][0]["code"] == "AIR"

        updated = client.patch(f"/api/categories/{child.json()['id']}", json={"description": "Flights"})
        assert updated.status_code == 200
        assert updated.json()["description"] == "Flights"
        deleted = client.delete(f"/api/categories/{child.json()['id']}")
        assert deleted.status_code == 204
