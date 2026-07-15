"""Phase 3: Add policy, policy_rule, and other expense management tables.

Revision ID: 002_add_policies
Revises: 001_baseline
Create Date: 2026-07-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_add_policies'
down_revision = '001_baseline'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # expense_categories table
    op.create_table(
        'expense_categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('parent_category_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('code', sa.String(100), nullable=False),
        sa.Column('name', sa.String(150), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('receipt_required', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('max_amount', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['parent_category_id'], ['expense_categories.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )
    op.create_index('expense_categories_code_key', 'expense_categories', ['code'], unique=True)
    op.create_index('expense_categories_is_deleted_idx', 'expense_categories', ['is_deleted'])

    # vendors table
    op.create_table(
        'vendors',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('normalized_name', sa.String(255), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('normalized_name'),
    )
    op.create_index('vendors_normalized_name_key', 'vendors', ['normalized_name'], unique=True)
    op.create_index('vendors_is_deleted_idx', 'vendors', ['is_deleted'])

    # policies table
    op.create_table(
        'policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('version_label', sa.String(50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('effective_from', sa.DateTime(), nullable=False),
        sa.Column('uploaded_document_attachment_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('policies_is_deleted_idx', 'policies', ['is_deleted'])

    # policy_rules table
    op.create_table(
        'policy_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('policy_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('vendor_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('max_per_day', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('max_per_trip', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('per_category_cap', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('receipt_required_above', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['category_id'], ['expense_categories.id']),
        sa.ForeignKeyConstraint(['policy_id'], ['policies.id']),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('policy_id', 'category_id', name='policy_rules_policy_id_category_id_key'),
    )
    op.create_index('policy_rules_is_deleted_idx', 'policy_rules', ['is_deleted'])


def downgrade() -> None:
    op.drop_index('policy_rules_is_deleted_idx', table_name='policy_rules')
    op.drop_table('policy_rules')
    op.drop_index('policies_is_deleted_idx', table_name='policies')
    op.drop_table('policies')
    op.drop_index('vendors_is_deleted_idx', table_name='vendors')
    op.drop_index('vendors_normalized_name_key', table_name='vendors')
    op.drop_table('vendors')
    op.drop_index('expense_categories_is_deleted_idx', table_name='expense_categories')
    op.drop_index('expense_categories_code_key', table_name='expense_categories')
    op.drop_table('expense_categories')
