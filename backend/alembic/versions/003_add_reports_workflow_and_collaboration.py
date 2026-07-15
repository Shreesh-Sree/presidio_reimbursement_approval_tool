"""Add expense reports, approvals, attachments, and notifications.

Revision ID: 003_reports_workflow
Revises: 002_add_policies
Create Date: 2026-07-15
"""

from alembic import op
import sqlalchemy as sa


revision = "003_reports_workflow"
down_revision = "002_add_policies"
branch_labels = None
depends_on = None


def _common_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "expense_reports",
        *_common_columns(),
        sa.Column("report_number", sa.String(50), nullable=False),
        sa.Column("employee_user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("department_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("workflow_rule_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("applied_policy_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("currency_code", sa.String(10), server_default=sa.text("'USD'"), nullable=False),
        sa.Column("status", sa.String(20), server_default=sa.text("'draft'"), nullable=False),
        sa.Column("total_amount", sa.Numeric(18, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("last_saved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ai_review_job_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("ai_review_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["employee_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.ForeignKeyConstraint(["workflow_rule_id"], ["workflow_rules.id"]),
        sa.ForeignKeyConstraint(["applied_policy_id"], ["policies.id"]),
        sa.UniqueConstraint("report_number", name="uq_expense_reports_report_number"),
    )
    op.create_index("ix_expense_reports_employee_status", "expense_reports", ["employee_user_id", "status"])
    op.create_index("ix_expense_reports_department_status", "expense_reports", ["department_id", "status"])
    op.create_index("ix_expense_reports_ai_review_job_id", "expense_reports", ["ai_review_job_id"])
    op.create_index("ix_expense_reports_is_deleted", "expense_reports", ["is_deleted"])

    op.create_table(
        "expense_items",
        *_common_columns(),
        sa.Column("expense_report_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("vendor_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("merchant_name", sa.String(255), nullable=True),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("original_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("currency_code", sa.String(10), nullable=True),
        sa.Column("exchange_rate", sa.Numeric(10, 6), nullable=True),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_policy_violated", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("policy_violation_reason", sa.Text(), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["expense_report_id"], ["expense_reports.id"]),
        sa.ForeignKeyConstraint(["category_id"], ["expense_categories.id"]),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"]),
        sa.UniqueConstraint("expense_report_id", "line_number", name="uq_expense_items_report_line"),
    )
    op.create_index("ix_expense_items_report", "expense_items", ["expense_report_id"])
    op.create_index("ix_expense_items_category", "expense_items", ["category_id"])
    op.create_index("ix_expense_items_is_deleted", "expense_items", ["is_deleted"])

    op.create_table(
        "attachments",
        *_common_columns(),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("original_file_name", sa.String(255), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(150), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("checksum", sa.String(128), nullable=False),
        sa.Column("uploaded_by", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"]),
    )
    op.create_index("ix_attachments_entity", "attachments", ["entity_type", "entity_id"])
    op.create_index("ix_attachments_checksum", "attachments", ["checksum"])
    op.create_index("ix_attachments_uploaded_by", "attachments", ["uploaded_by"])
    op.create_index("ix_attachments_is_deleted", "attachments", ["is_deleted"])

    op.create_table(
        "approval_levels",
        *_common_columns(),
        sa.Column("expense_report_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("approver_user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("level_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("decision_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_parallel", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["expense_report_id"], ["expense_reports.id"]),
        sa.ForeignKeyConstraint(["approver_user_id"], ["users.id"]),
        sa.UniqueConstraint("expense_report_id", "level_number", "approver_user_id", name="uq_approval_levels_report_level_approver"),
    )
    op.create_index("ix_approval_levels_approver_status", "approval_levels", ["approver_user_id", "status"])
    op.create_index("ix_approval_levels_status", "approval_levels", ["status"])
    op.create_index("ix_approval_levels_is_deleted", "approval_levels", ["is_deleted"])

    op.create_table(
        "approval_history",
        *_common_columns(),
        sa.Column("expense_report_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("approval_level_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("performed_by", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("performed_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["expense_report_id"], ["expense_reports.id"]),
        sa.ForeignKeyConstraint(["approval_level_id"], ["approval_levels.id"]),
        sa.ForeignKeyConstraint(["performed_by"], ["users.id"]),
    )
    op.create_index("ix_approval_history_report_performed", "approval_history", ["expense_report_id", "performed_at"])
    op.create_index("ix_approval_history_approval_level", "approval_history", ["approval_level_id"])
    op.create_index("ix_approval_history_action", "approval_history", ["action"])
    op.create_index("ix_approval_history_performer_performed", "approval_history", ["performed_by", "performed_at"])
    op.create_index("ix_approval_history_is_deleted", "approval_history", ["is_deleted"])

    op.create_table(
        "comments",
        *_common_columns(),
        sa.Column("expense_report_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("parent_comment_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("visibility", sa.String(20), server_default=sa.text("'public'"), nullable=False),
        sa.Column("comment_text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["expense_report_id"], ["expense_reports.id"]),
        sa.ForeignKeyConstraint(["parent_comment_id"], ["comments.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_comments_report_created", "comments", ["expense_report_id", "created_at"])
    op.create_index("ix_comments_parent", "comments", ["parent_comment_id"])
    op.create_index("ix_comments_user", "comments", ["user_id"])
    op.create_index("ix_comments_visibility", "comments", ["visibility"])
    op.create_index("ix_comments_is_deleted", "comments", ["is_deleted"])

    op.create_table(
        "notifications",
        *_common_columns(),
        sa.Column("recipient_user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("template_code", sa.String(100), nullable=False),
        sa.Column("channel", sa.String(20), server_default=sa.text("'in_app'"), nullable=False),
        sa.Column("status", sa.String(20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivery_error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"]),
    )
    op.create_index("ix_notifications_recipient_created", "notifications", ["recipient_user_id", "created_at"])
    op.create_index("ix_notifications_channel", "notifications", ["channel"])
    op.create_index("ix_notifications_status", "notifications", ["status"])
    op.create_index("ix_notifications_sent_at", "notifications", ["sent_at"])
    op.create_index("ix_notifications_is_deleted", "notifications", ["is_deleted"])

    op.create_table(
        "payment_records",
        *_common_columns(),
        sa.Column("expense_report_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("bank_detail_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("payment_reference", sa.String(150), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=True),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("status", sa.String(20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("processed_by", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["expense_report_id"], ["expense_reports.id"]),
        sa.ForeignKeyConstraint(["processed_by"], ["users.id"]),
        sa.UniqueConstraint("payment_reference", name="uq_payment_records_reference"),
    )
    op.create_index("ix_payment_records_expense_report", "payment_records", ["expense_report_id"])
    op.create_index("ix_payment_records_bank_detail", "payment_records", ["bank_detail_id"])
    op.create_index("ix_payment_records_status_date", "payment_records", ["status", "payment_date"])
    op.create_index("ix_payment_records_processed_by", "payment_records", ["processed_by"])
    op.create_index("ix_payment_records_is_deleted", "payment_records", ["is_deleted"])


def downgrade() -> None:
    for table_name in (
        "payment_records",
        "notifications",
        "comments",
        "approval_history",
        "approval_levels",
        "attachments",
        "expense_items",
        "expense_reports",
    ):
        op.drop_table(table_name)
