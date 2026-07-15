"""Small, transaction-friendly audit-log writer used by every domain service."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def _json(value: Any | None) -> str | None:
    if value is None:
        return None
    return json.dumps(value, default=str, sort_keys=True)


def record_audit(
    db: Session | None,
    entity_name: str,
    record_id: str,
    operation: str,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    performed_by: str | None = None,
    request_meta: dict[str, Any] | None = None,
) -> AuditLog | dict[str, Any]:
    """Add an audit entry to the caller's unit of work.

    The legacy ``db=None`` return shape remains useful for pure unit tests, but
    production calls persist the real :class:`AuditLog` row without committing
    independently.  That makes state changes and their audit trail atomic.
    """

    values = {
        "entity_name": entity_name,
        "record_id": str(record_id),
        "operation": operation,
        "before_json": _json(before),
        "after_json": _json(after),
        "performed_by": str(performed_by) if performed_by else None,
        "request_meta": _json(request_meta),
    }
    if db is None:
        return values

    entry = AuditLog(**values)
    db.add(entry)
    return entry
