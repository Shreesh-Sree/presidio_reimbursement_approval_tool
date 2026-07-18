"""Supabase JWT verification for OAuth-authenticated sessions.

Supabase Auth signs user access tokens with ES256 (asymmetric). The public
key is provided via SUPABASE_JWT_SECRET (for legacy HS256) or fetched from
the project's JWKS endpoint (for ES256). Application roles remain in our
database; the token supplies only a verified external subject and email for
allowlist lookup.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import jwt
from email_validator import EmailNotValidError, validate_email
from jwt import PyJWKClient

from app.core.config import Settings


class SupabaseConfigurationError(RuntimeError):
    """Raised when Supabase JWT verification is not configured."""


class SupabaseTokenError(ValueError):
    """Raised for a malformed, invalid, or insufficient Supabase token."""


@dataclass(frozen=True)
class SupabaseIdentity:
    """The verified identity surface used for application authorization."""

    subject: str
    email: str


def _normalise_email(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SupabaseTokenError("OAuth token does not contain an email")
    try:
        return validate_email(value.strip(), check_deliverability=False).normalized.lower()
    except EmailNotValidError as exc:
        raise SupabaseTokenError("OAuth token contains an invalid email") from exc


def _verified_email(claims: dict[str, Any]) -> str:
    role = claims.get("role")
    if role != "authenticated":
        raise SupabaseTokenError("OAuth token does not belong to an authenticated user")
    return _normalise_email(claims.get("email"))


def _required_configuration(settings: Settings) -> tuple[str, str]:
    issuer = settings.supabase_url.strip().rstrip("/")
    jwt_secret = settings.supabase_jwt_secret.strip()
    if not issuer:
        raise SupabaseConfigurationError("Supabase JWT verification is not fully configured")
    return issuer, jwt_secret


@lru_cache(maxsize=4)
def _jwks_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url, cache_keys=True, timeout=5)


def _get_signing_key(token: str, settings: Settings):
    """Get signing key from embedded JWKS or remote endpoint."""
    import json as _json
    from jwt import PyJWK

    if settings.supabase_jwks:
        jwks_data = _json.loads(settings.supabase_jwks)
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        for key_data in jwks_data.get("keys", []):
            if key_data.get("kid") == kid:
                return PyJWK(key_data).key
        raise SupabaseTokenError("No matching key found in SUPABASE_JWKS")

    issuer = settings.supabase_url.strip().rstrip("/")
    jwks_url = f"{issuer}/auth/v1/.well-known/jwks.json"
    client = _jwks_client(jwks_url)
    return client.get_signing_key_from_jwt(token).key


def verify_supabase_token(token: str, settings: Settings) -> SupabaseIdentity:
    """Verify a Supabase access token and return the identity claims needed for authorization."""

    issuer, jwt_secret = _required_configuration(settings)
    expected_issuer = f"{issuer}/auth/v1"

    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "")

        if alg == "HS256":
            if not jwt_secret:
                raise SupabaseConfigurationError("SUPABASE_JWT_SECRET required for HS256 tokens")
            claims = jwt.decode(
                token,
                jwt_secret,
                algorithms=["HS256"],
                issuer=expected_issuer,
                audience="authenticated",
                options={"require": ["exp", "iat", "sub", "iss"]},
                leeway=60,
            )
        elif alg in ("ES256", "RS256"):
            signing_key = _get_signing_key(token, settings)
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=[alg],
                issuer=expected_issuer,
                audience="authenticated",
                options={"require": ["exp", "iat", "sub", "iss"]},
                leeway=60,
            )
        else:
            raise SupabaseTokenError(f"Unsupported token algorithm: {alg}")
    except (SupabaseTokenError, SupabaseConfigurationError):
        raise
    except Exception as exc:
        raise SupabaseTokenError("OAuth token could not be verified") from exc

    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject.strip() or len(subject) > 255:
        raise SupabaseTokenError("OAuth token has an invalid subject")

    return SupabaseIdentity(subject=subject.strip(), email=_verified_email(claims))
