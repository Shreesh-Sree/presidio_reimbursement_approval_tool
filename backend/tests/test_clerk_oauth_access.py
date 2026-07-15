"""OAuth-only auth: signed Clerk identity, email allowlist, and first admin."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.clerk import (
    ClerkConfigurationError,
    ClerkIdentity,
    ClerkTokenError,
    _verified_email,
    verify_clerk_token,
)
from app.core.config import Settings
from app.models.user import User


def _clerk_settings(*, super_admin_email: str = "owner@example.com") -> Settings:
    return Settings(
        database_url="sqlite+pysqlite:///:memory:",
        jwt_secret="test-secret",
        s3_bucket="test-bucket",
        auth_provider="clerk",
        clerk_jwks_url="https://clerk.example.test/.well-known/jwks.json",
        clerk_issuer="https://clerk.example.test",
        clerk_audience="presidio-api",
        clerk_authorized_parties="http://localhost:5173",
        super_admin_email=super_admin_email,
    )


def _oauth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer signed-clerk-session-token"}


def _mock_clerk_identity(monkeypatch, identity: ClerkIdentity, settings: Settings) -> None:
    import app.core.deps as deps

    monkeypatch.setattr(deps, "get_settings", lambda: settings)
    monkeypatch.setattr(deps, "verify_clerk_token", lambda _token, _settings: identity)


def test_configured_super_admin_is_provisioned_on_first_verified_oauth_login(client, db, monkeypatch):
    settings = _clerk_settings()
    _mock_clerk_identity(
        monkeypatch,
        ClerkIdentity(subject="user_owner", email="owner@example.com"),
        settings,
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
    _mock_clerk_identity(
        monkeypatch,
        ClerkIdentity(subject="user_unlisted", email="unlisted@example.com"),
        _clerk_settings(),
    )

    response = client.get("/api/auth/me", headers=_oauth_headers())

    assert response.status_code == 403
    assert response.json()["detail"] == {
        "code": "access_not_granted",
        "message": "Your account has not been granted access to this platform.",
    }


def test_allowlisted_user_binds_first_clerk_subject_and_rejects_a_later_mismatch(
    client, seeded_user, db, monkeypatch
):
    db.commit()
    settings = _clerk_settings()
    _mock_clerk_identity(
        monkeypatch,
        ClerkIdentity(subject="user_employee", email="employee@example.com"),
        settings,
    )

    allowed = client.get("/api/auth/me", headers=_oauth_headers())
    assert allowed.status_code == 200, allowed.text
    db.refresh(seeded_user)
    assert seeded_user.external_auth_subject == "user_employee"

    _mock_clerk_identity(
        monkeypatch,
        ClerkIdentity(subject="user_someone_else", email="employee@example.com"),
        settings,
    )
    denied = client.get("/api/auth/me", headers=_oauth_headers())
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "access_not_granted"


def test_first_admin_bootstrap_race_reuses_the_allowlist_row(db, seeded_user, monkeypatch):
    """A concurrent first OAuth request must not turn into a transient 500."""

    from app.services import oauth_access_service

    seeded_user.email = "owner@example.com"
    db.commit()
    settings = _clerk_settings()
    identity = ClerkIdentity(subject="user_owner", email="owner@example.com")
    calls = iter(([], [seeded_user]))
    monkeypatch.setattr(oauth_access_service, "_active_users_for_email", lambda *_args: next(calls))

    def losing_bootstrap(*_args, **_kwargs):
        raise IntegrityError("insert users", {}, RuntimeError("unique constraint"))

    monkeypatch.setattr(oauth_access_service, "_bootstrap_super_administrator", losing_bootstrap)

    user = oauth_access_service.resolve_oauth_user(db, identity=identity, settings=settings)

    assert user.id == seeded_user.id
    assert user.external_auth_subject == "user_owner"


def test_clerk_token_requires_the_custom_verified_email_claims():
    assert _verified_email({"email": "person@example.com", "email_verified": True}) == "person@example.com"
    with pytest.raises(ClerkTokenError):
        _verified_email({"email": "person@example.com", "email_verified": False})
    with pytest.raises(ClerkTokenError):
        _verified_email({"email": "person@example.com"})


def test_clerk_verifier_requires_rs256_and_checks_authorized_party(monkeypatch):
    import app.core.clerk as clerk

    settings = _clerk_settings()
    monkeypatch.setattr(clerk.jwt, "get_unverified_header", lambda _token: {"alg": "RS256"})
    monkeypatch.setattr(
        clerk,
        "_jwks_client",
        lambda _url: type("Client", (), {"get_signing_key_from_jwt": lambda self, _token: type("Key", (), {"key": "public-key"})()})(),
    )
    monkeypatch.setattr(
        clerk.jwt,
        "decode",
        lambda *_args, **_kwargs: {
            "sub": "user_123",
            "email": "person@example.com",
            "email_verified": True,
            "azp": "http://localhost:5173/",
        },
    )

    identity = verify_clerk_token("signed-token", settings)
    assert identity == ClerkIdentity(subject="user_123", email="person@example.com")

    monkeypatch.setattr(clerk.jwt, "get_unverified_header", lambda _token: {"alg": "HS256"})
    with pytest.raises(ClerkTokenError):
        verify_clerk_token("wrong-algorithm", settings)


def test_clerk_verifier_rejects_incomplete_configuration():
    settings = _clerk_settings()
    settings.clerk_jwks_url = ""
    with pytest.raises(ClerkConfigurationError):
        verify_clerk_token("signed-token", settings)


def test_password_endpoints_are_gone_in_clerk_mode(client, monkeypatch):
    import app.api.routes.auth as auth_routes

    monkeypatch.setattr(auth_routes, "get_settings", lambda: _clerk_settings())
    response = client.post(
        "/api/auth/login",
        json={"email": "owner@example.com", "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 410
    assert response.json()["detail"]["code"] == "oauth_only"
