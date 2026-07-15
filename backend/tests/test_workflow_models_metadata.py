"""Metadata coverage for the workflow and status persistence tables."""

import uuid

from app.core.database import Base
from app.models.approval_history import ApprovalHistory
from app.models.approval_level import ApprovalLevel
from app.models.attachment import Attachment
from app.models.comment import Comment
from app.models.delegation import Delegation
from app.models.notification import Notification
from app.models.payment_record import PaymentRecord
from app.models.session import Session
from app.models.workflow_rule import WorkflowRule


def test_workflow_status_models_register_the_expected_tables() -> None:
    # Referencing the classes keeps imports intentional and makes this test fail
    # if a module stops registering its model with the shared metadata.
    models = (
        ApprovalLevel,
        ApprovalHistory,
        Attachment,
        Comment,
        Delegation,
        Notification,
        PaymentRecord,
        Session,
        WorkflowRule,
    )

    assert {model.__tablename__ for model in models} <= set(Base.metadata.tables)


def test_workflow_status_models_keep_the_key_contract_columns() -> None:
    tables = Base.metadata.tables

    assert {"expense_report_id", "approver_user_id", "level_number", "status"} <= set(
        tables["approval_levels"].c.keys()
    )
    assert {"expense_report_id", "approval_level_id", "action", "performed_by"} <= set(
        tables["approval_history"].c.keys()
    )
    assert {"entity_type", "entity_id", "storage_path", "checksum"} <= set(
        tables["attachments"].c.keys()
    )
    assert {"expense_report_id", "parent_comment_id", "user_id", "comment_text"} <= set(
        tables["comments"].c.keys()
    )
    assert {"recipient_user_id", "channel", "payload", "read_at"} <= set(
        tables["notifications"].c.keys()
    )
    assert {"session_token_hash", "expires_at", "revoked_at"} <= set(tables["sessions"].c.keys())


def test_notification_and_comment_keep_service_compatible_attribute_names() -> None:
    notification = Notification(
        recipient_user_id=uuid.uuid4(),
        template_code="report.submitted",
        payload_json={"report_id": "report-1"},
    )
    comment = Comment(
        expense_report_id=uuid.uuid4(),
        author_user_id=uuid.uuid4(),
        text="Please add the receipt.",
    )

    assert notification.payload == {"report_id": "report-1"}
    assert comment.user_id == comment.author_user_id
    assert comment.comment_text == comment.text
