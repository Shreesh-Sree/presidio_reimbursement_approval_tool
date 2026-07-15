import json
from sqlalchemy.orm import Session


class AuditLog:
    """Placeholder for AuditLog model."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def record_audit(
    db: Session,
    entity_name: str,
    record_id: str,
    operation: str,
    before: dict | None = None,
    after: dict | None = None,
    performed_by: str | None = None,
    request_meta: str | None = None,
):
    """Record an audit log entry."""
    log = {
        "entity_name": entity_name,
        "record_id": record_id,
        "operation": operation,
        "before_json": json.dumps(before) if before else None,
        "after_json": json.dumps(after) if after else None,
        "performed_by": performed_by,
        "request_meta": request_meta,
    }
    return log
