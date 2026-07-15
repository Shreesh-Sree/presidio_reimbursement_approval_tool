"""Add finance payment batches, events, and idempotent payment records.

Revision ID: 004_payment_operations
Revises: 003_reports_workflow
Create Date: 2026-07-15
"""

from alembic import op
import sqlalchemy as sa


revision = "004_payment_operations"
down_revision = "003_reports_workflow"
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
        "payment_batches",
        *_common_columns(),
        sa.Column("organization_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("batch_reference", sa.String(150), nullable=False),
        sa.Column("status", sa.String(20), server_default=sa.text("'created'"), nullable=False),
        sa.Column("currency_code", sa.String(10), nullable=False),
        sa.Column("total_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("payment_count", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("exported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.UniqueConstraint("organization_id", "batch_reference", name="uq_payment_batches_org_reference"),
    )
    op.create_index(
        "ix_payment_batches_organization_status",
        "payment_batches",
        ["organization_id", "status"],
    )
    op.create_index("ix_payment_batches_created_by", "payment_batches", ["created_by"])
    op.create_index("ix_payment_batches_is_deleted", "payment_batches", ["is_deleted"])

    # Batch mode keeps this migration runnable for the repository's SQLite
    # verification path while emitting ordinary ALTER operations on PostgreSQL.
    with op.batch_alter_table("payment_records") as batch_op:
        batch_op.add_column(sa.Column("payment_batch_id", sa.Uuid(as_uuid=True), nullable=True))
        batch_op.add_column(sa.Column("provider_reference", sa.String(150), nullable=True))
        batch_op.add_column(sa.Column("failure_reason", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("exported_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_foreign_key(
            "fk_payment_records_payment_batch_id_payment_batches",
            "payment_batches",
            ["payment_batch_id"],
            ["id"],
        )
        batch_op.create_unique_constraint("uq_payment_records_expense_report", ["expense_report_id"])
        batch_op.create_index("ix_payment_records_batch_status", ["payment_batch_id", "status"])

    op.create_table(
        "payment_events",
        *_common_columns(),
        sa.Column("payment_record_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("payment_batch_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("from_status", sa.String(20), nullable=True),
        sa.Column("to_status", sa.String(20), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("provider_reference", sa.String(150), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("performed_by", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["payment_record_id"], ["payment_records.id"]),
        sa.ForeignKeyConstraint(["payment_batch_id"], ["payment_batches.id"]),
        sa.ForeignKeyConstraint(["performed_by"], ["users.id"]),
    )
    op.create_index("ix_payment_events_payment_occurred", "payment_events", ["payment_record_id", "occurred_at"])
    op.create_index("ix_payment_events_batch", "payment_events", ["payment_batch_id"])
    op.create_index("ix_payment_events_performed", "payment_events", ["performed_by", "occurred_at"])
    op.create_index("ix_payment_events_is_deleted", "payment_events", ["is_deleted"])


def downgrade() -> None:
    op.drop_table("payment_events")

    with op.batch_alter_table("payment_records") as batch_op:
        batch_op.drop_index("ix_payment_records_batch_status")
        batch_op.drop_constraint("uq_payment_records_expense_report", type_="unique")
        batch_op.drop_constraint(
            "fk_payment_records_payment_batch_id_payment_batches",
            type_="foreignkey",
        )
        batch_op.drop_column("exported_at")
        batch_op.drop_column("failure_reason")
        batch_op.drop_column("provider_reference")
        batch_op.drop_column("payment_batch_id")

    op.drop_table("payment_batches")
