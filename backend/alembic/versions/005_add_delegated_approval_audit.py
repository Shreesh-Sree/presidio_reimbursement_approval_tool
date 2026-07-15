"""Preserve delegation provenance and SLA timestamps on approval tasks.

Revision ID: 005_delegated_approvals
Revises: 004_payment_operations
Create Date: 2026-07-15
"""

from alembic import op
import sqlalchemy as sa


revision = "005_delegated_approvals"
down_revision = "004_payment_operations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Batch mode is intentionally used so the repository's SQLite migration
    # verification stays meaningful while PostgreSQL emits regular ALTERs.
    with op.batch_alter_table("approval_levels") as batch_op:
        batch_op.add_column(sa.Column("original_approver_user_id", sa.Uuid(as_uuid=True), nullable=True))
        batch_op.add_column(sa.Column("delegation_id", sa.Uuid(as_uuid=True), nullable=True))
        batch_op.add_column(sa.Column("due_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("reminder_sent_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_foreign_key(
            "fk_approval_levels_original_approver_user_id_users",
            "users",
            ["original_approver_user_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_approval_levels_delegation_id_delegations",
            "delegations",
            ["delegation_id"],
            ["id"],
        )
        batch_op.create_index("ix_approval_levels_original_approver_status", ["original_approver_user_id", "status"])
        batch_op.create_index("ix_approval_levels_due_status", ["due_at", "status"])

    # Existing reports retain their original assignee as the original owner.
    # New rows are populated by the workflow service before commit.
    op.execute("UPDATE approval_levels SET original_approver_user_id = approver_user_id WHERE original_approver_user_id IS NULL")

    with op.batch_alter_table("approval_history") as batch_op:
        batch_op.add_column(sa.Column("acting_for_user_id", sa.Uuid(as_uuid=True), nullable=True))
        batch_op.alter_column(
            "performed_by",
            existing_type=sa.Uuid(as_uuid=True),
            nullable=True,
        )
        batch_op.create_foreign_key(
            "fk_approval_history_acting_for_user_id_users",
            "users",
            ["acting_for_user_id"],
            ["id"],
        )
        batch_op.create_index("ix_approval_history_acting_for_performed", ["acting_for_user_id", "performed_at"])


def downgrade() -> None:
    # The legacy column is non-nullable and has no system actor equivalent.
    # Delegate decisions can be attributed to their original approver; pure
    # automation events cannot be represented safely by the old schema, so a
    # downgrade deliberately removes only those audit rows rather than invent
    # a human actor.
    op.execute(
        "UPDATE approval_history SET performed_by = acting_for_user_id "
        "WHERE performed_by IS NULL AND acting_for_user_id IS NOT NULL"
    )
    op.execute("DELETE FROM approval_history WHERE performed_by IS NULL")

    with op.batch_alter_table("approval_history") as batch_op:
        batch_op.alter_column(
            "performed_by",
            existing_type=sa.Uuid(as_uuid=True),
            nullable=False,
        )
        batch_op.drop_index("ix_approval_history_acting_for_performed")
        batch_op.drop_constraint("fk_approval_history_acting_for_user_id_users", type_="foreignkey")
        batch_op.drop_column("acting_for_user_id")

    with op.batch_alter_table("approval_levels") as batch_op:
        batch_op.drop_index("ix_approval_levels_due_status")
        batch_op.drop_index("ix_approval_levels_original_approver_status")
        batch_op.drop_constraint("fk_approval_levels_delegation_id_delegations", type_="foreignkey")
        batch_op.drop_constraint("fk_approval_levels_original_approver_user_id_users", type_="foreignkey")
        batch_op.drop_column("escalated_at")
        batch_op.drop_column("reminder_sent_at")
        batch_op.drop_column("due_at")
        batch_op.drop_column("delegation_id")
        batch_op.drop_column("original_approver_user_id")
