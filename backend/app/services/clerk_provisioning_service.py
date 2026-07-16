"""Small, server-only boundary for Clerk invitation provisioning.

Restricted sign-up instances should invite users instead of creating a
passwordless Clerk user directly.  Clerk creates the authenticated account
only when the recipient accepts the invitation, while the application keeps
the pre-approved user, role and reporting-line record ready for first sign-in.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import Settings


class ClerkProvisioningError(Exception):
    """A safe, actionable error from Clerk's server-side invitation API."""

    def __init__(self, detail: str, status_code: int = 502) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


@dataclass(frozen=True)
class ClerkInvitation:
    id: str
    email: str


def _error_detail(payload: object) -> str:
    if isinstance(payload, dict):
        errors = payload.get("errors")
        if isinstance(errors, list) and errors and isinstance(errors[0], dict):
            message = errors[0].get("long_message") or errors[0].get("message")
            if isinstance(message, str) and message:
                return message
    return "Clerk could not create the invitation"


def invite_user(
    *,
    settings: Settings,
    email: str,
    full_name: str,
    organization_id: str,
) -> ClerkInvitation:
    """Create and email a Clerk invitation for one administrator-created user."""

    if not settings.clerk_secret_key:
        raise ClerkProvisioningError(
            "Clerk user provisioning is not configured. Set CLERK_SECRET_KEY on the API service.",
            503,
        )

    payload: dict[str, object] = {
        "email_address": email,
        "notify": True,
        "public_metadata": {
            "presidio_organization_id": organization_id,
            "presidio_full_name": full_name,
        },
    }
    if settings.clerk_invitation_redirect_url:
        payload["redirect_url"] = settings.clerk_invitation_redirect_url

    request = Request(
        "https://api.clerk.com/v1/invitations",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.clerk_secret_key}",
            "Content-Type": "application/json",
            "User-Agent": "presidio-reimbursement-api/1.0",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:  # nosec B310 - fixed Clerk API URL
            response_payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            detail = _error_detail(json.loads(exc.read().decode("utf-8")))
        except (UnicodeDecodeError, json.JSONDecodeError):
            detail = "Clerk could not create the invitation"
        if exc.code == 429:
            detail = "Clerk invitation limit reached. Try again after the stated retry period."
        raise ClerkProvisioningError(detail, 429 if exc.code == 429 else 502) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise ClerkProvisioningError("Clerk invitation service is temporarily unavailable") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ClerkProvisioningError("Clerk returned an invalid invitation response") from exc

    invitation_id = response_payload.get("id") if isinstance(response_payload, dict) else None
    if not isinstance(invitation_id, str) or not invitation_id:
        raise ClerkProvisioningError("Clerk returned an invalid invitation response")
    return ClerkInvitation(id=invitation_id, email=email)


def revoke_invitation(*, settings: Settings, invitation_id: str) -> None:
    """Best-effort compensation if the local transaction cannot be created."""

    if not settings.clerk_secret_key or not invitation_id:
        return
    request = Request(
        f"https://api.clerk.com/v1/invitations/{invitation_id}/revoke",
        headers={"Authorization": f"Bearer {settings.clerk_secret_key}"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=10):  # nosec B310 - invitation id is Clerk-issued
            return
    except (HTTPError, URLError, TimeoutError, OSError):
        # The original domain error is more useful to the administrator. The
        # audit trail will still show the failed local creation attempt.
        return
