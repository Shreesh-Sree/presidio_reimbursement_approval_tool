"""Add policy, category, vendor, and structured-rule persistence.

Revision ID: 002_add_policies
Revises: 001_baseline
Create Date: 2026-07-15
"""

from alembic import op
import sqlalchemy as sa


revision = "002_add_policies"
down_revision = "001_baseline"
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
        "expense_categories",
        *_common_columns(),
        sa.Column("parent_category_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("receipt_required", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("max_amount", sa.Numeric(18, 2), nullable=True),
        sa.ForeignKeyConstraint(["parent_category_id"], ["expense_categories.id"]),
        sa.UniqueConstraint("code", name="uq_expense_categories_code"),
    )
    op.create_index("ix_expense_categories_is_deleted", "expense_categories", ["is_deleted"])

    op.create_table(
        "vendors",
        *_common_columns(),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("normalized_name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.UniqueConstraint("normalized_name", name="uq_vendors_normalized_name"),
    )
    op.create_index("ix_vendors_is_deleted", "vendors", ["is_deleted"])

    op.create_table(
        "policies",
        *_common_columns(),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version_label", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uploaded_document_attachment_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.UniqueConstraint("name", "version_label", name="uq_policies_name_version"),
    )
    op.create_index("ix_policies_is_active", "policies", ["is_active"])
    op.create_index("ix_policies_is_deleted", "policies", ["is_deleted"])

    op.create_table(
        "policy_rules",
        *_common_columns(),
        sa.Column("policy_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("category_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("vendor_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("max_per_day", sa.Numeric(18, 2), nullable=True),
        sa.Column("max_per_trip", sa.Numeric(18, 2), nullable=True),
        sa.Column("per_category_cap", sa.Numeric(18, 2), nullable=True),
        sa.Column("receipt_required_above", sa.Numeric(18, 2), nullable=True),
        sa.ForeignKeyConstraint(["policy_id"], ["policies.id"]),
        sa.ForeignKeyConstraint(["category_id"], ["expense_categories.id"]),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"]),
        sa.UniqueConstraint("policy_id", "category_id", "vendor_id", name="uq_policy_rules_scope"),
    )
    op.create_index("ix_policy_rules_is_deleted", "policy_rules", ["is_deleted"])


def downgrade() -> None:
    op.drop_table("policy_rules")
    op.drop_table("policies")
    op.drop_table("vendors")
    op.drop_table("expense_categories")
