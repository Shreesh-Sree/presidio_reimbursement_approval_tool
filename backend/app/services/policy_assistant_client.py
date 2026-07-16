"""Narrow core boundary for the isolated policy-assistant RAG service.

The core API does not import the assistant package or its SQLite persistence.
It can only pass administrator-supplied policy text and opaque tenant/version
references over an optional, authenticated HTTP boundary.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import uuid
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import get_settings


class PolicyAssistantError(RuntimeError):
    """Safe error for an unavailable or malformed optional assistant service."""


def _service_url() -> str | None:
    value = (os.getenv("POLICY_ASSISTANT_SERVICE_URL", "").strip() or get_settings().policy_assistant_service_url.strip()).rstrip("/")
    return value or None


def _timeout() -> float:
    try:
        return max(0.1, min(30.0, float(os.getenv("POLICY_ASSISTANT_TIMEOUT_SECONDS", "") or get_settings().policy_assistant_timeout_seconds)))
    except ValueError:
        return 4.0


def _reference_hmac_key() -> bytes:
    """Return the stable secret used to pseudonymize core identifiers.

    Deployments should set a dedicated key so policy scopes survive bearer-token
    rotation. Falling back to the existing service token keeps the optional
    integration safe for current installations while still using a keyed hash.
    """

    key = os.getenv("POLICY_ASSISTANT_REFERENCE_HMAC_KEY", "").strip() or get_settings().policy_assistant_reference_hmac_key.strip()
    if not key:
        key = os.getenv("POLICY_ASSISTANT_SERVICE_TOKEN", "").strip() or get_settings().policy_assistant_service_token.strip()
    if not key:
        raise PolicyAssistantError("Policy assistant reference key is not configured")
    return key.encode("utf-8")


def _normalized_uuid(value: uuid.UUID | str) -> uuid.UUID:
    try:
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise PolicyAssistantError("Policy assistant received an invalid opaque reference") from exc


def _keyed_ref(prefix: str, material: str) -> str:
    digest = hmac.new(
        _reference_hmac_key(),
        f"presidio:policy-assistant:v1:{prefix}:{material}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{prefix}-{digest}"


def _opaque_ref(prefix: str, value: uuid.UUID | str) -> str:
    """Pseudonymize a core UUID without exporting it to the assistant."""

    return _keyed_ref(prefix, _normalized_uuid(value).hex)


def _document_ref(policy_id: uuid.UUID | str, content_digest: str) -> str:
    """Return a deterministic, non-reversible document reference for one version."""

    return _keyed_ref("document", f"{_normalized_uuid(policy_id).hex}:{content_digest}")


def _request(method: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    base_url = _service_url()
    if not base_url:
        raise PolicyAssistantError("Policy assistant is not configured")
    token = os.getenv("POLICY_ASSISTANT_SERVICE_TOKEN", "").strip() or get_settings().policy_assistant_service_token.strip()
    if not token:
        raise PolicyAssistantError("Policy assistant credentials are not configured")
    encoded = json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")
    request = Request(
        f"{base_url}{path}",
        data=encoded,
        method=method,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Request-ID": uuid.uuid4().hex,
        },
    )
    try:
        with urlopen(request, timeout=_timeout()) as response:  # nosec B310: endpoint is deployment configuration
            decoded = response.read().decode("utf-8")
    except HTTPError as exc:
        raise PolicyAssistantError(f"Policy assistant returned HTTP {exc.code}") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise PolicyAssistantError("Policy assistant is unavailable") from exc
    try:
        body = json.loads(decoded)
    except json.JSONDecodeError as exc:
        raise PolicyAssistantError("Policy assistant returned invalid JSON") from exc
    if not isinstance(body, dict):
        raise PolicyAssistantError("Policy assistant returned an invalid payload")
    return body


def _scope(organization_id: uuid.UUID | str, policy_id: uuid.UUID | str) -> tuple[str, str]:
    return _opaque_ref("tenant", organization_id), _opaque_ref("policy", policy_id)


def index_policy_text(
    *,
    organization_id: uuid.UUID | str,
    policy_id: uuid.UUID | str,
    content: str,
) -> dict[str, Any]:
    """Index administrator-supplied policy evidence in the assistant's own store."""

    cleaned_content = content.strip()
    if not cleaned_content:
        raise PolicyAssistantError("Policy text is required for indexing")
    if len(cleaned_content) > 50_000:
        raise PolicyAssistantError("Policy text must be 50,000 characters or fewer")
    tenant_ref, policy_version_ref = _scope(organization_id, policy_id)
    content_digest = hashlib.sha256(cleaned_content.encode("utf-8")).hexdigest()
    document_ref = _document_ref(policy_id, content_digest)
    return _request(
        "POST",
        "/v1/policy-documents",
        {
            "tenant_ref": tenant_ref,
            "policy_version_ref": policy_version_ref,
            "document_ref": document_ref,
            "content": cleaned_content,
        },
    )


def ask_policy(
    *,
    organization_id: uuid.UUID | str,
    policy_id: uuid.UUID | str,
    question: str,
    top_k: int | None = None,
) -> dict[str, Any]:
    """Ask a policy question; answer/citations remain advisory and read-only."""

    cleaned_question = question.strip()
    if not cleaned_question:
        raise PolicyAssistantError("A policy question is required")
    if len(cleaned_question) > 1_200:
        raise PolicyAssistantError("Policy questions must be 1,200 characters or fewer")
    tenant_ref, policy_version_ref = _scope(organization_id, policy_id)
    payload: dict[str, Any] = {
        "tenant_ref": tenant_ref,
        "policy_version_ref": policy_version_ref,
        "question": cleaned_question,
    }
    if top_k is not None:
        payload["top_k"] = top_k
    return _request("POST", "/v1/ask", payload)
