"""Minimal, dependency-light Clerk session-token verification.

The core API deliberately verifies a short-lived Clerk JWT itself rather than
trusting browser-provided email/role headers.  Application roles remain in the
core database; the OAuth token supplies only a verified external subject and
email for allowlist lookup.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import jwt
from email_validator import EmailNotValidError, validate_email
from jwt import PyJWKClient

from app.core.config import Settings


class ClerkConfigurationError(RuntimeError):
    """Raised when a Clerk deployment is missing required verification config."""


class ClerkTokenError(ValueError):
    """Raised for a malformed, invalid, or insufficient Clerk session token."""


@dataclass(frozen=True)
class ClerkIdentity:
    """The small, verified identity surface used for application authorization."""

    subject: str
    email: str


def _normalise_email(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ClerkTokenError("OAuth token does not contain an email")
    try:
        return validate_email(value.strip(), check_deliverability=False).normalized.lower()
    except EmailNotValidError as exc:
        raise ClerkTokenError("OAuth token contains an invalid email") from exc


def _verified_email(claims: dict[str, Any]) -> str:
    value = claims.get("email_verified")
    # Clerk templates can encode boolean shortcodes as either native booleans
    # or the string representation.  Do not accept a missing/false value.
    is_verified = value is True or (isinstance(value, str) and value.lower() == "true")
    if not is_verified:
        raise ClerkTokenError("OAuth token does not contain a verified email")
    return _normalise_email(claims.get("email"))


def _required_configuration(settings: Settings) -> tuple[str, str, str]:
    jwks_url = settings.clerk_jwks_url.strip()
    issuer = settings.clerk_issuer.strip().rstrip("/")
    audience = settings.clerk_audience.strip()
    if not jwks_url or not issuer or not audience:
        raise ClerkConfigurationError("Clerk JWT verification is not fully configured")
    return jwks_url, issuer, audience


@lru_cache(maxsize=8)
def _jwks_client(jwks_url: str) -> PyJWKClient:
    """Cache public keys by explicitly configured Clerk JWKS URL."""

    return PyJWKClient(jwks_url, cache_keys=True)


def verify_clerk_token(token: str, settings: Settings) -> ClerkIdentity:
    """Verify one bearer token and return only the claims authorization needs.

    The Clerk dashboard must define the ``presidio-api`` custom JWT template
    (or configured equivalent) with ``email`` and ``email_verified`` claims.
    ``aud`` and ``azp`` are checked so a token from another application cannot
    be replayed against this API.
    """

    jwks_url, issuer, audience = _required_configuration(settings)
    try:
        header = jwt.get_unverified_header(token)
        if header.get("alg") != "RS256":
            raise ClerkTokenError("OAuth token uses an unsupported signing algorithm")
        signing_key = _jwks_client(jwks_url).get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=audience,
            issuer=issuer,
            options={"require": ["exp", "iat", "nbf", "iss", "sub", "aud"]},
            leeway=60,
        )
    except ClerkTokenError:
        raise
    except Exception as exc:  # PyJWT's exception hierarchy changes between releases.
        raise ClerkTokenError("OAuth token could not be verified") from exc

    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject.strip() or len(subject) > 255:
        raise ClerkTokenError("OAuth token has an invalid subject")

    allowed_parties = settings.clerk_authorized_parties_list
    if allowed_parties:
        azp = claims.get("azp")
        if not isinstance(azp, str) or azp.rstrip("/") not in allowed_parties:
            raise ClerkTokenError("OAuth token was issued for another application")

    return ClerkIdentity(subject=subject.strip(), email=_verified_email(claims))
