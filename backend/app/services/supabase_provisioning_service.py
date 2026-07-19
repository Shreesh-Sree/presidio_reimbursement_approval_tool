"""Server-only boundary for Supabase user invitation provisioning.

When users are created by administrators, this service invites them through
the Supabase Auth admin API so they receive an email and can set up their
account. The application keeps the pre-approved user, role and reporting-line
record ready for first sign-in.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import Settings


class SupabaseProvisioningError(Exception):
    """A safe, actionable error from Supabase's server-side admin API."""

    def __init__(self, detail: str, status_code: int = 502) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


@dataclass(frozen=True)
class SupabaseInvitation:
    id: str
    email: str


def invite_user(
    *,
    settings: Settings,
    email: str,
    full_name: str,
    organization_id: str,
) -> SupabaseInvitation:
    """Invite a user through the Supabase Auth admin API."""

    if not settings.supabase_service_role_key:
        raise SupabaseProvisioningError(
            "Supabase user provisioning is not configured. Set SUPABASE_SERVICE_ROLE_KEY on the API service.",
            503,
        )
    if not settings.supabase_url:
        raise SupabaseProvisioningError(
            "Supabase URL is not configured. Set SUPABASE_URL on the API service.",
            503,
        )

    payload: dict[str, object] = {
        "email": email,
        "data": {
            "full_name": full_name,
            "organization_id": organization_id,
        },
    }

    base_url = settings.supabase_url.strip().rstrip("/")
    request = Request(
        f"{base_url}/auth/v1/invite",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "apikey": settings.supabase_service_role_key,
            "Content-Type": "application/json",
            "User-Agent": "presidio-reimbursement-api/1.0",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:  # nosec B310
            response_payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            error_body = json.loads(exc.read().decode("utf-8"))
            detail = error_body.get("msg") or error_body.get("message") or "Supabase could not create the invitation"
        except (UnicodeDecodeError, json.JSONDecodeError):
            detail = "Supabase could not create the invitation"
        if exc.code == 429:
            detail = "Supabase invitation rate limit reached. Try again later."
            status_code = 429
        elif exc.code in {401, 403}:
            # This is an API-service configuration failure, not a browser or
            # user credential failure.  Do not expose Supabase's raw response
            # because it can reveal key-validation details.
            detail = (
                "Supabase user provisioning credentials were rejected. "
                "Rotate SUPABASE_SERVICE_ROLE_KEY on the API service."
            )
            status_code = 503
        elif exc.code in {400, 422}:
            # The admin is the authenticated caller of this endpoint, so an
            # upstream invitation validation error is actionable input feedback.
            status_code = 422
        elif exc.code >= 500:
            detail = "Supabase invitation service is temporarily unavailable"
            status_code = 503
        else:
            status_code = 502
        raise SupabaseProvisioningError(detail, status_code) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise SupabaseProvisioningError("Supabase invitation service is temporarily unavailable") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SupabaseProvisioningError("Supabase returned an invalid invitation response") from exc

    user_id = response_payload.get("id") if isinstance(response_payload, dict) else None
    if not isinstance(user_id, str) or not user_id:
        raise SupabaseProvisioningError("Supabase returned an invalid invitation response")
    return SupabaseInvitation(id=user_id, email=email)


def revoke_invitation(*, settings: Settings, invitation_id: str) -> None:
    """Best-effort: delete the invited user from Supabase Auth if local creation fails."""

    if not settings.supabase_service_role_key or not invitation_id:
        return
    base_url = settings.supabase_url.strip().rstrip("/")
    request = Request(
        f"{base_url}/auth/v1/admin/users/{invitation_id}",
        headers={
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "apikey": settings.supabase_service_role_key,
        },
        method="DELETE",
    )
    try:
        with urlopen(request, timeout=10):  # nosec B310
            return
    except (HTTPError, URLError, TimeoutError, OSError):
        return
