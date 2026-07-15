import json
from app.services.audit_service import record_audit


def test_record_audit():
    log = record_audit(
        None,
        entity_name="users",
        record_id="user-123",
        operation="create",
        after={"email": "user@example.com"},
        performed_by="admin-id",
    )
    
    assert log["entity_name"] == "users"
    assert log["record_id"] == "user-123"
    assert log["operation"] == "create"
    assert json.loads(log["after_json"])["email"] == "user@example.com"
    assert log["performed_by"] == "admin-id"
