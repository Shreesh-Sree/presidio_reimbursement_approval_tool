"""No-network coverage for the server-only Supabase invitation boundary."""

from __future__ import annotations

import io
import json
from urllib.error import HTTPError

import pytest

from app.core.config import Settings
from app.services import supabase_provisioning_service


def _settings(**changes: str) -> Settings:
    values = {
        "database_url": "sqlite+pysqlite:///:memory:",
        "jwt_secret": "test-secret",
        "s3_bucket": "test-bucket",
        "auth_provider": "supabase",
        "supabase_url": "https://test.supabase.co",
        "supabase_jwt_secret": "test-supabase-jwt-secret",
        "supabase_service_role_key": "sbp_test_service_role_key",
    }
    values.update(changes)
    return Settings(**values)


def test_invite_user_posts_supabase_invitation(monkeypatch):
    captured: dict[str, object] = {}

    class Response:
        def read(self):
            return b'{"id":"user_123","email":"employee@example.com"}'

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr(supabase_provisioning_service, "urlopen", fake_urlopen)
    invitation = supabase_provisioning_service.invite_user(
        settings=_settings(),
        email="employee@example.com",
        full_name="Employee Example",
        organization_id="org_123",
    )

    assert invitation.id == "user_123"
    assert captured["url"] == "https://test.supabase.co/auth/v1/invite"
    assert captured["body"] == {
        "email": "employee@example.com",
        "data": {
            "full_name": "Employee Example",
            "organization_id": "org_123",
        },
    }


def test_invite_user_requires_service_role_key():
    with pytest.raises(supabase_provisioning_service.SupabaseProvisioningError, match="SUPABASE_SERVICE_ROLE_KEY"):
        supabase_provisioning_service.invite_user(
            settings=_settings(supabase_service_role_key=""),
            email="employee@example.com",
            full_name="Employee Example",
            organization_id="org_123",
        )


def test_invite_user_turns_rate_limit_into_retryable_error(monkeypatch):
    def fake_urlopen(_request, timeout):
        raise HTTPError(
            "https://test.supabase.co/auth/v1/invite",
            429,
            "Too many requests",
            hdrs=None,
            fp=io.BytesIO(b'{"msg":"rate limit exceeded"}'),
        )

    monkeypatch.setattr(supabase_provisioning_service, "urlopen", fake_urlopen)
    with pytest.raises(supabase_provisioning_service.SupabaseProvisioningError, match="rate limit") as error:
        supabase_provisioning_service.invite_user(
            settings=_settings(),
            email="employee@example.com",
            full_name="Employee Example",
            organization_id="org_123",
        )
    assert error.value.status_code == 429
