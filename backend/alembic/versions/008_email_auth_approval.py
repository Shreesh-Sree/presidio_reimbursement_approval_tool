"""add email auth and pending approval status

Revision ID: 008_email_auth_approval
Revises: 007_oauth_identity
Create Date: 2026-07-18 17:20:52.698942

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '008_email_auth_approval'
down_revision: Union[str, Sequence[str], None] = '007_oauth_identity'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add pending_approval user status and user_access_requests table."""

    # SQLite cannot ``ALTER TABLE ... DROP/ADD CONSTRAINT``.  Batch mode
    # recreates the table there while remaining a normal schema change on
    # PostgreSQL.  Earlier revisions did not always create this check, so only
    # drop it when the target database actually has the named constraint.
    existing_checks = {
        check.get("name")
        for check in sa.inspect(op.get_bind()).get_check_constraints("users")
    }
    with op.batch_alter_table("users") as batch_op:
        if "users_status_check" in existing_checks:
            batch_op.drop_constraint("users_status_check", type_="check")
        batch_op.create_check_constraint(
            "users_status_check",
            "status IN ('active', 'inactive', 'pending_approval')",
        )

    # Create user_access_requests table
    op.create_table(
        'user_access_requests',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('requested_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approved_by_user_id', sa.Uuid(), nullable=True),
        sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejected_by_user_id', sa.Uuid(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('user_id', sa.Uuid(), nullable=True),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(['approved_by_user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['rejected_by_user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email', name='uq_user_access_request_email')
    )
    op.create_index('ix_user_access_requests_status', 'user_access_requests', ['status'])
    op.create_index('ix_user_access_requests_organization_id', 'user_access_requests', ['organization_id'])


def downgrade() -> None:
    """Remove pending_approval status and user_access_requests table."""
    op.drop_index('ix_user_access_requests_organization_id')
    op.drop_index('ix_user_access_requests_status')
    op.drop_table('user_access_requests')

    existing_checks = {
        check.get("name")
        for check in sa.inspect(op.get_bind()).get_check_constraints("users")
    }
    with op.batch_alter_table("users") as batch_op:
        if "users_status_check" in existing_checks:
            batch_op.drop_constraint("users_status_check", type_="check")
        batch_op.create_check_constraint(
            "users_status_check",
            "status IN ('active', 'inactive')",
        )
