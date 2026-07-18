"""Support OAuth-only allowlist accounts without local passwords.

Revision ID: 007_oauth_identity
Revises: 006_policy_tenant_scope
Create Date: 2026-07-15

The application retains historical password hashes during an explicit local
migration/testing mode, but an OAuth-created allowlist entry has no password
at all.  The provider's immutable external subject is linked once on first login so a
reused email address cannot silently take over an existing account.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "007_oauth_identity"
down_revision = "006_policy_tenant_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("external_auth_subject", sa.String(length=255), nullable=True))
        batch_op.alter_column("password_hash", existing_type=sa.Text(), nullable=True)
        batch_op.create_unique_constraint("uq_users_external_auth_subject", ["external_auth_subject"])


def downgrade() -> None:
    bind = op.get_bind()
    users = sa.Table("users", sa.MetaData(), autoload_with=bind)
    missing_password = bind.execute(
        sa.select(users.c.id).where(users.c.password_hash.is_(None)).limit(1)
    ).first()
    if missing_password is not None:
        raise RuntimeError(
            "Cannot downgrade OAuth identity support while passwordless OAuth accounts exist."
        )

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("uq_users_external_auth_subject", type_="unique")
        batch_op.drop_column("external_auth_subject")
        batch_op.alter_column("password_hash", existing_type=sa.Text(), nullable=False)
