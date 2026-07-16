"""No-network coverage for the server-only Clerk invitation boundary."""

from __future__ import annotations

import io
import json
from urllib.error import HTTPError

import pytest

from app.core.config import Settings
from app.services import clerk_provisioning_service


def _settings(**changes: str) -> Settings:
    values = {
        "database_url": "sqlite+pysqlite:///:memory:",
        "jwt_secret": "test-secret",
        "s3_bucket": "test-bucket",
        "auth_provider": "clerk",
        "clerk_secret_key": "sk_test_server_only",
        "clerk_invitation_redirect_url": "https://presidio.example.test/sign-in",
    }
    values.update(changes)
    return Settings(**values)


def test_invite_user_posts_clerk_invitation_with_presidio_metadata(monkeypatch):
    captured: dict[str, object] = {}

    class Response:
        def read(self):
            return b'{"id":"inv_123"}'

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr(clerk_provisioning_service, "urlopen", fake_urlopen)
    invitation = clerk_provisioning_service.invite_user(
        settings=_settings(),
        email="employee@example.com",
        full_name="Employee Example",
        organization_id="org_123",
    )

    assert invitation.id == "inv_123"
    assert captured["url"] == "https://api.clerk.com/v1/invitations"
    assert captured["body"] == {
        "email_address": "employee@example.com",
        "notify": True,
        "public_metadata": {
            "presidio_organization_id": "org_123",
            "presidio_full_name": "Employee Example",
        },
        "redirect_url": "https://presidio.example.test/sign-in",
    }


def test_invite_user_requires_server_only_clerk_key():
    with pytest.raises(clerk_provisioning_service.ClerkProvisioningError, match="CLERK_SECRET_KEY"):
        clerk_provisioning_service.invite_user(
            settings=_settings(clerk_secret_key=""),
            email="employee@example.com",
            full_name="Employee Example",
            organization_id="org_123",
        )


def test_invite_user_turns_clerk_rate_limit_into_retryable_error(monkeypatch):
    def fake_urlopen(_request, timeout):
        raise HTTPError(
            "https://api.clerk.com/v1/invitations",
            429,
            "Too many requests",
            hdrs=None,
            fp=io.BytesIO(b'{"errors":[{"message":"rate limited"}]}'),
        )

    monkeypatch.setattr(clerk_provisioning_service, "urlopen", fake_urlopen)
    with pytest.raises(clerk_provisioning_service.ClerkProvisioningError, match="limit reached") as error:
        clerk_provisioning_service.invite_user(
            settings=_settings(),
            email="employee@example.com",
            full_name="Employee Example",
            organization_id="org_123",
        )
    assert error.value.status_code == 429
