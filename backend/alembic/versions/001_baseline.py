"""Create the core identity, audit, and workflow-rule schema.

Revision ID: 001_baseline
Revises:
Create Date: 2026-07-15

The expense/policy tables intentionally arrive in later revisions.  This keeps
foreign keys valid at every point in the migration chain and lets a fresh
deployment be upgraded without an undocumented bootstrap database.
"""

from alembic import op
import sqlalchemy as sa


revision = "001_baseline"
down_revision = None
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
        "organizations",
        *_common_columns(),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("base_currency", sa.String(10), server_default=sa.text("'INR'"), nullable=False),
        sa.Column("status", sa.String(20), server_default=sa.text("'active'"), nullable=False),
        sa.UniqueConstraint("code", name="uq_organizations_code"),
    )
    op.create_index("ix_organizations_status", "organizations", ["status"])

    op.create_table(
        "departments",
        *_common_columns(),
        sa.Column("organization_id", sa.Uuid(as_uuid=True), nullable=False),
        # No FK: a department may exist before its first employee is created.
        sa.Column("department_head_user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), server_default=sa.text("'active'"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.UniqueConstraint("organization_id", "code", name="uq_department_org_code"),
    )
    op.create_index("ix_departments_organization_id", "departments", ["organization_id"])
    op.create_index("ix_departments_department_head_user_id", "departments", ["department_head_user_id"])
    op.create_index("ix_departments_status", "departments", ["status"])

    op.create_table(
        "users",
        *_common_columns(),
        sa.Column("organization_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("department_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("manager_user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("employee_number", sa.String(50), nullable=False),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("designation", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("status", sa.String(20), server_default=sa.text("'active'"), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.ForeignKeyConstraint(["manager_user_id"], ["users.id"]),
        sa.UniqueConstraint("organization_id", "employee_number", name="uq_user_org_employee_number"),
        sa.UniqueConstraint("organization_id", "username", name="uq_user_org_username"),
        sa.UniqueConstraint("organization_id", "email", name="uq_user_org_email"),
    )
    op.create_index("ix_users_organization_id", "users", ["organization_id"])
    op.create_index("ix_users_department_id", "users", ["department_id"])
    op.create_index("ix_users_manager_user_id", "users", ["manager_user_id"])
    op.create_index("ix_users_status", "users", ["status"])

    op.create_table(
        "roles",
        *_common_columns(),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_system_role", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.UniqueConstraint("code", name="uq_roles_code"),
    )
    op.create_index("ix_roles_is_active", "roles", ["is_active"])

    op.create_table(
        "permissions",
        *_common_columns(),
        sa.Column("code", sa.String(150), nullable=False),
        sa.Column("module", sa.String(100), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.UniqueConstraint("code", name="uq_permissions_code"),
        sa.UniqueConstraint("module", "action", name="uq_permission_module_action"),
    )
    op.create_index("ix_permissions_is_active", "permissions", ["is_active"])

    op.create_table(
        "user_roles",
        *_common_columns(),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("role_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),
    )

    op.create_table(
        "role_permissions",
        *_common_columns(),
        sa.Column("role_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("permission_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"]),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_permission"),
    )

    op.create_table(
        "workflow_rules",
        *_common_columns(),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("conditions_json", sa.JSON(), nullable=False),
        sa.Column("approval_chain_json", sa.JSON(), nullable=False),
        sa.Column("priority", sa.Integer(), server_default=sa.text("100"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.UniqueConstraint("name", name="uq_workflow_rules_name"),
    )
    op.create_index("ix_workflow_rules_priority_active", "workflow_rules", ["priority", "is_active"])
    op.create_index("ix_workflow_rules_is_deleted", "workflow_rules", ["is_deleted"])

    op.create_table(
        "audit_logs",
        *_common_columns(),
        sa.Column("entity_name", sa.String(100), nullable=False),
        sa.Column("record_id", sa.String(36), nullable=False),
        sa.Column("operation", sa.String(50), nullable=False),
        sa.Column("before_json", sa.Text(), nullable=True),
        sa.Column("after_json", sa.Text(), nullable=True),
        sa.Column("performed_by", sa.String(36), nullable=True),
        sa.Column("request_meta", sa.Text(), nullable=True),
    )
    op.create_index("ix_audit_logs_entity_record", "audit_logs", ["entity_name", "record_id"])

    op.create_table(
        "sessions",
        *_common_columns(),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("session_token_hash", sa.Text(), nullable=False),
        sa.Column("ip_address", sa.String(100), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("session_token_hash", name="uq_sessions_token_hash"),
    )
    op.create_index("ix_sessions_user_expires", "sessions", ["user_id", "expires_at"])
    op.create_index("ix_sessions_revoked_at", "sessions", ["revoked_at"])
    op.create_index("ix_sessions_is_deleted", "sessions", ["is_deleted"])

    op.create_table(
        "delegations",
        *_common_columns(),
        sa.Column("delegator_user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("delegate_user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scope", sa.String(20), server_default=sa.text("'all'"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["delegator_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["delegate_user_id"], ["users.id"]),
    )
    op.create_index("ix_delegations_delegator_delegate_dates", "delegations", ["delegator_user_id", "delegate_user_id", "start_date", "end_date"])
    op.create_index("ix_delegations_delegate", "delegations", ["delegate_user_id"])
    op.create_index("ix_delegations_scope", "delegations", ["scope"])
    op.create_index("ix_delegations_is_active", "delegations", ["is_active"])
    op.create_index("ix_delegations_is_deleted", "delegations", ["is_deleted"])


def downgrade() -> None:
    for table_name in (
        "delegations",
        "sessions",
        "audit_logs",
        "workflow_rules",
        "role_permissions",
        "user_roles",
        "permissions",
        "roles",
        "users",
        "departments",
        "organizations",
    ):
        op.drop_table(table_name)
