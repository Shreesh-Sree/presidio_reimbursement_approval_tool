"""OAuth-only auth: signed Supabase identity, email allowlist, and first admin."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.supabase_auth import (
    SupabaseConfigurationError,
    SupabaseIdentity,
    SupabaseTokenError,
    _verified_email,
    verify_supabase_token,
)
from app.core.config import Settings
from app.models.user import User
from app.services.supabase_provisioning_service import SupabaseInvitation


def _supabase_settings(*, super_admin_email: str = "owner@example.com") -> Settings:
    return Settings(
        database_url="sqlite+pysqlite:///:memory:",
        jwt_secret="test-secret",
        s3_bucket="test-bucket",
        auth_provider="supabase",
        supabase_url="https://test.supabase.co",
        supabase_jwt_secret="test-supabase-jwt-secret",
        super_admin_email=super_admin_email,
    )


def _oauth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer signed-clerk-session-token"}


def _mock_supabase_identity(monkeypatch, identity: SupabaseIdentity, settings: Settings) -> None:
    import app.api.routes.auth as auth_routes
    import app.core.deps as deps

    monkeypatch.setattr(deps, "get_settings", lambda: settings)
    monkeypatch.setattr(deps, "verify_supabase_token", lambda _token, _settings: identity)
    monkeypatch.setattr(auth_routes, "get_settings", lambda: settings)


def test_configured_super_admin_is_provisioned_on_first_verified_oauth_login(client, db, monkeypatch):
    import app.api.routes.users as users_routes

    settings = _supabase_settings()
    _mock_supabase_identity(
        monkeypatch,
        SupabaseIdentity(subject="user_owner", email="owner@example.com"),
        settings,
    )
    monkeypatch.setattr(
        users_routes.supabase_provisioning_service,
        "invite_user",
        lambda **kwargs: SupabaseInvitation(id="inv_test", email=kwargs["email"]),
    )

    response = client.get("/api/auth/me", headers=_oauth_headers())

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["email"] == "owner@example.com"
    assert payload["roles"] == ["administrator"]
    assert "user:create" in payload["permissions"]
    user = db.query(User).filter(User.email == "owner@example.com").one()
    assert user.external_auth_subject == "user_owner"
    assert user.password_hash is None

    allowlisted = client.post(
        "/api/users",
        headers=_oauth_headers(),
        json={
            "email": "teammate@example.com",
            "full_name": "Teammate",
            "roles": ["employee"],
        },
    )
    assert allowlisted.status_code == 201, allowlisted.text
    assert allowlisted.json()["oauth_status"] == "invited"
    teammate = db.query(User).filter(User.email == "teammate@example.com").one()
    assert teammate.password_hash is None

    # Repeated API authentication must use the one provisioned account rather
    # than inserting an administrator on every request.
    again = client.get("/api/auth/me", headers=_oauth_headers())
    assert again.status_code == 200
    assert db.query(User).filter(User.email == "owner@example.com").count() == 1


def test_verified_email_not_on_allowlist_receives_explicit_access_denied_page_signal(client, monkeypatch):
    _mock_supabase_identity(
        monkeypatch,
        SupabaseIdentity(subject="user_unlisted", email="unlisted@example.com"),
        _supabase_settings(),
    )

    response = client.get("/api/auth/me", headers=_oauth_headers())

    assert response.status_code == 403
    assert response.json()["detail"] == {
        "code": "access_not_granted",
        "message": "Your account has not been granted access to this platform.",
    }


def test_allowlisted_user_binds_first_subject_and_rejects_later_mismatch(
    client, seeded_user, db, monkeypatch
):
    db.commit()
    settings = _supabase_settings()
    _mock_supabase_identity(
        monkeypatch,
        SupabaseIdentity(subject="user_employee", email="employee@example.com"),
        settings,
    )

    allowed = client.get("/api/auth/me", headers=_oauth_headers())
    assert allowed.status_code == 200, allowed.text
    db.refresh(seeded_user)
    assert seeded_user.external_auth_subject == "user_employee"

    _mock_supabase_identity(
        monkeypatch,
        SupabaseIdentity(subject="user_someone_else", email="employee@example.com"),
        settings,
    )
    denied = client.get("/api/auth/me", headers=_oauth_headers())
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "access_not_granted"


def test_existing_allowlisted_user_records_each_completed_oauth_session(client, seeded_user, db, monkeypatch):
    previous_login = datetime(2026, 1, 1, tzinfo=UTC)
    seeded_user.external_auth_subject = "user_employee"
    seeded_user.last_login_at = previous_login
    db.commit()
    _mock_supabase_identity(
        monkeypatch,
        SupabaseIdentity(subject="user_employee", email="employee@example.com"),
        _supabase_settings(),
    )

    response = client.get("/api/auth/me", headers=_oauth_headers())

    assert response.status_code == 200, response.text
    db.refresh(seeded_user)
    assert seeded_user.last_login_at is not None
    recorded_login = seeded_user.last_login_at
    if recorded_login.tzinfo is None:  # SQLite does not round-trip timezone metadata.
        recorded_login = recorded_login.replace(tzinfo=UTC)
    assert recorded_login > previous_login


def test_soft_deleted_identity_binding_returns_controlled_access_denied(client, seeded_user, db, monkeypatch):
    seeded_user.external_auth_subject = "user_retired"
    seeded_user.is_deleted = True
    replacement = User(
        organization_id=seeded_user.organization_id,
        department_id=seeded_user.department_id,
        employee_number="E-002",
        username="replacement",
        email="replacement@example.com",
        full_name="Replacement Employee",
        status="active",
    )
    db.add(replacement)
    db.commit()
    _mock_supabase_identity(
        monkeypatch,
        SupabaseIdentity(subject="user_retired", email="replacement@example.com"),
        _supabase_settings(),
    )

    response = client.get("/api/auth/me", headers=_oauth_headers())

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "access_not_granted"


def test_first_admin_bootstrap_race_reuses_the_allowlist_row(db, seeded_user, monkeypatch):
    """A concurrent first OAuth request must not turn into a transient 500."""

    from app.services import oauth_access_service

    seeded_user.email = "owner@example.com"
    db.commit()
    settings = _supabase_settings()
    identity = SupabaseIdentity(subject="user_owner", email="owner@example.com")
    calls = iter(([], [seeded_user]))
    monkeypatch.setattr(oauth_access_service, "_active_users_for_email", lambda *_args: next(calls))

    def losing_bootstrap(*_args, **_kwargs):
        raise IntegrityError("insert users", {}, RuntimeError("unique constraint"))

    monkeypatch.setattr(oauth_access_service, "_bootstrap_super_administrator", losing_bootstrap)

    user = oauth_access_service.resolve_oauth_user(db, identity=identity, settings=settings)

    assert user.id == seeded_user.id
    assert user.external_auth_subject == "user_owner"


def test_supabase_token_requires_verified_email_claims():
    assert _verified_email({"email": "person@example.com", "role": "authenticated"}) == "person@example.com"
    with pytest.raises(SupabaseTokenError):
        _verified_email({"email": "person@example.com", "role": "anon"})
    with pytest.raises(SupabaseTokenError):
        _verified_email({"email": "person@example.com", "role": ""})


def test_supabase_verifier_validates_token(monkeypatch):
    import app.core.supabase_auth as supabase_auth

    settings = _supabase_settings()
    monkeypatch.setattr(
        supabase_auth.jwt,
        "get_unverified_header",
        lambda _token: {"alg": "HS256", "typ": "JWT"},
    )
    monkeypatch.setattr(
        supabase_auth.jwt,
        "decode",
        lambda *_args, **_kwargs: {
            "sub": "user_123",
            "email": "person@example.com",
            "role": "authenticated",
        },
    )

    identity = verify_supabase_token("signed-token", settings)
    assert identity == SupabaseIdentity(subject="user_123", email="person@example.com")

    monkeypatch.setattr(
        supabase_auth.jwt,
        "decode",
        lambda *_args, **_kwargs: {
            "sub": "user_123",
            "email": "person@example.com",
        },
    )
    with pytest.raises(SupabaseTokenError):
        verify_supabase_token("unconfirmed-email", settings)


def test_supabase_verifier_rejects_incomplete_configuration():
    settings = _supabase_settings()
    settings.supabase_url = ""
    with pytest.raises(SupabaseConfigurationError):
        verify_supabase_token("signed-token", settings)


def test_password_endpoints_are_gone_in_supabase_mode(client, monkeypatch):
    import app.api.routes.auth as auth_routes

    monkeypatch.setattr(auth_routes, "get_settings", lambda: _supabase_settings())
    response = client.post(
        "/api/auth/login",
        json={"email": "owner@example.com", "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 410
    assert response.json()["detail"]["code"] == "oauth_only"
