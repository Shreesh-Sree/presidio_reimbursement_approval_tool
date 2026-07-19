"""Make tenant-owned domain data explicit and add durable delivery state.

Revision ID: 009_tenant_workflows_outbox
Revises: 008_email_auth_approval
Create Date: 2026-07-19

Workflow rules, categories, and vendors were historically global rows.  This
revision uses evidence from existing report/policy references when possible and
quarantines ambiguous legacy rows rather than assigning them to an arbitrary
tenant.  New rows are protected by non-null ownership and tenant-scoped unique
constraints.
"""

from __future__ import annotations

import json
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from typing import Iterable

from alembic import op
import sqlalchemy as sa


# Alembic's legacy version table is commonly VARCHAR(32), including in the
# PostgreSQL baseline used by deployed environments. Keep this identifier
# portable across that schema contract; the descriptive filename is unchanged.
revision = "009_tenant_workflows_outbox"
down_revision = "008_email_auth_approval"
branch_labels = None
depends_on = None


def _key(value: object) -> str:
    return str(value)


def _bind_uuid(bind, value: object) -> object:
    return _key(value) if bind.dialect.name == "sqlite" else value


def _quarantine_organization(bind, organizations: sa.Table) -> object:
    prefix = "LEGACY-DOMAIN-QUARANTINE"
    existing_codes = {str(code) for (code,) in bind.execute(sa.select(organizations.c.code)).all()}
    code = prefix
    suffix = 2
    while code in existing_codes:
        code = f"{prefix[:45]}-{suffix}"
        suffix += 1
    organization_id = uuid.uuid4()
    now = datetime.now(UTC)
    bind.execute(
        sa.insert(organizations).values(
            id=_bind_uuid(bind, organization_id),
            created_at=now,
            updated_at=now,
            deleted_at=None,
            is_deleted=False,
            version=1,
            name="Legacy Domain Data Quarantine",
            code=code,
            base_currency="INR",
            status="inactive",
        )
    )
    return organization_id


def _active_organizations(bind, organizations: sa.Table) -> list[object]:
    return [
        organization_id
        for organization_id, status, is_deleted in bind.execute(
            sa.select(organizations.c.id, organizations.c.status, organizations.c.is_deleted)
        ).all()
        if not is_deleted and status == "active"
    ]


def _scope_candidates(bind, table_name: str, column_name: str) -> dict[str, set[object]]:
    """Infer catalogue ownership only from concrete policy/report references."""

    metadata = sa.MetaData()
    items = sa.Table("expense_items", metadata, autoload_with=bind)
    reports = sa.Table("expense_reports", metadata, autoload_with=bind)
    users = sa.Table("users", metadata, autoload_with=bind)
    policy_rules = sa.Table("policy_rules", metadata, autoload_with=bind)
    policies = sa.Table("policies", metadata, autoload_with=bind)
    candidates: dict[str, set[object]] = defaultdict(set)

    item_column = getattr(items.c, column_name)
    for value, organization_id in bind.execute(
        sa.select(item_column, users.c.organization_id)
        .select_from(items.join(reports, items.c.expense_report_id == reports.c.id).join(users, reports.c.employee_user_id == users.c.id))
        .where(item_column.is_not(None))
    ).all():
        if value is not None and organization_id is not None:
            candidates[_key(value)].add(organization_id)

    rule_column = getattr(policy_rules.c, column_name)
    for value, organization_id in bind.execute(
        sa.select(rule_column, policies.c.organization_id)
        .select_from(policy_rules.join(policies, policy_rules.c.policy_id == policies.c.id))
        .where(rule_column.is_not(None))
    ).all():
        if value is not None and organization_id is not None:
            candidates[_key(value)].add(organization_id)
    return candidates


def _json_organization(value: object, active_ids: Iterable[object]) -> object | None:
    try:
        payload = json.loads(value) if isinstance(value, str) else value
        candidate = (payload or {}).get("organization_id") if isinstance(payload, dict) else None
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if candidate is None:
        return None
    for organization_id in active_ids:
        if _key(organization_id) == _key(candidate):
            return organization_id
    return None


def _backfill_workflows(bind) -> None:
    metadata = sa.MetaData()
    organizations = sa.Table("organizations", metadata, autoload_with=bind)
    workflows = sa.Table("workflow_rules", metadata, autoload_with=bind)
    active_ids = _active_organizations(bind, organizations)
    quarantine_id: object | None = None
    single = active_ids[0] if len(active_ids) == 1 else None
    for workflow_id, conditions in bind.execute(
        sa.select(workflows.c.id, workflows.c.conditions_json).where(workflows.c.organization_id.is_(None))
    ).all():
        organization_id = _json_organization(conditions, active_ids) or single
        values: dict[str, object] = {}
        if organization_id is None:
            quarantine_id = quarantine_id or _quarantine_organization(bind, organizations)
            organization_id = quarantine_id
            # Never permit an ambiguous legacy workflow to route submissions.
            values["is_active"] = False
        values["organization_id"] = _bind_uuid(bind, organization_id)
        bind.execute(sa.update(workflows).where(workflows.c.id == workflow_id).values(**values))


def _backfill_catalog(bind, table_name: str, column_name: str) -> None:
    metadata = sa.MetaData()
    organizations = sa.Table("organizations", metadata, autoload_with=bind)
    table = sa.Table(table_name, metadata, autoload_with=bind)
    active_ids = _active_organizations(bind, organizations)
    candidates = _scope_candidates(bind, table_name, column_name)
    quarantine_id: object | None = None
    single = active_ids[0] if len(active_ids) == 1 else None
    for (row_id,) in bind.execute(sa.select(table.c.id).where(table.c.organization_id.is_(None))).all():
        row_candidates = candidates.get(_key(row_id), set())
        # A concrete multi-tenant reference is ambiguous even when only one
        # of those tenants is currently active.  Assigning it to the active
        # tenant would make previously shared catalogue data mutable by that
        # tenant, so quarantine it.  The single-active-tenant shortcut is
        # reserved for genuinely unreferenced legacy data.
        if len(row_candidates) == 1:
            organization_id = next(iter(row_candidates))
        elif not row_candidates and single is not None:
            organization_id = single
        else:
            organization_id = None
        if organization_id is None:
            quarantine_id = quarantine_id or _quarantine_organization(bind, organizations)
            organization_id = quarantine_id
        bind.execute(
            sa.update(table)
            .where(table.c.id == row_id)
            .values(organization_id=_bind_uuid(bind, organization_id))
        )


def _scope_workflow_rules() -> None:
    bind = op.get_bind()
    op.add_column("workflow_rules", sa.Column("organization_id", sa.Uuid(as_uuid=True), nullable=True))
    _backfill_workflows(bind)
    with op.batch_alter_table("workflow_rules") as batch_op:
        batch_op.drop_constraint("uq_workflow_rules_name", type_="unique")
        batch_op.alter_column("organization_id", existing_type=sa.Uuid(as_uuid=True), nullable=False)
        batch_op.create_foreign_key(
            "fk_workflow_rules_organization_id_organizations",
            "organizations",
            ["organization_id"],
            ["id"],
        )
        batch_op.create_unique_constraint("uq_workflow_rules_organization_name", ["organization_id", "name"])
        batch_op.create_index(
            "ix_workflow_rules_organization_priority_active",
            ["organization_id", "priority", "is_active"],
        )
    op.create_index("ix_workflow_rules_organization_id", "workflow_rules", ["organization_id"])


def _scope_catalog(
    table_name: str,
    reference_column: str,
    unique_column: str,
    old_unique: str,
    new_unique: str,
) -> None:
    bind = op.get_bind()
    op.add_column(table_name, sa.Column("organization_id", sa.Uuid(as_uuid=True), nullable=True))
    _backfill_catalog(bind, table_name, reference_column)
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.drop_constraint(old_unique, type_="unique")
        batch_op.alter_column("organization_id", existing_type=sa.Uuid(as_uuid=True), nullable=False)
        batch_op.create_foreign_key(
            f"fk_{table_name}_organization_id_organizations",
            "organizations",
            ["organization_id"],
            ["id"],
        )
        batch_op.create_unique_constraint(new_unique, ["organization_id", unique_column])
    op.create_index(f"ix_{table_name}_organization_id", table_name, ["organization_id"])


def _create_outbox() -> None:
    op.create_table(
        "integration_outbox",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("aggregate_type", sa.String(100), nullable=False),
        sa.Column("aggregate_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("dedupe_key", sa.String(255), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("locked_by", sa.String(100), nullable=True),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("dedupe_key", name="uq_integration_outbox_dedupe_key"),
    )
    op.create_index("ix_integration_outbox_ready", "integration_outbox", ["status", "available_at"])
    op.create_index("ix_integration_outbox_lease", "integration_outbox", ["locked_until"])


def _add_notification_delivery_state() -> None:
    with op.batch_alter_table("notifications") as batch_op:
        batch_op.add_column(sa.Column("delivery_attempts", sa.Integer(), server_default=sa.text("0"), nullable=False))
        batch_op.add_column(sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("delivery_claim_token", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("delivery_claimed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("delivery_lease_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_notifications_delivery_ready", "notifications", ["channel", "status", "next_attempt_at"])
    op.create_index("ix_notifications_delivery_lease", "notifications", ["delivery_lease_expires_at"])


def _add_access_request_permission() -> None:
    """Keep the administrator permission catalog deployable with the route."""

    bind = op.get_bind()
    metadata = sa.MetaData()
    permissions = sa.Table("permissions", metadata, autoload_with=bind)
    roles = sa.Table("roles", metadata, autoload_with=bind)
    role_permissions = sa.Table("role_permissions", metadata, autoload_with=bind)
    permission_id = bind.execute(
        sa.select(permissions.c.id).where(permissions.c.code == "access_request:manage")
    ).scalar_one_or_none()
    now = datetime.now(UTC)
    if permission_id is None:
        permission_id = uuid.uuid4()
        bind.execute(
            sa.insert(permissions).values(
                id=_bind_uuid(bind, permission_id),
                created_at=now,
                updated_at=now,
                deleted_at=None,
                is_deleted=False,
                version=1,
                code="access_request:manage",
                module="access_request",
                action="manage",
                description="Review and decide public access requests",
                is_active=True,
            )
        )
    for (role_id,) in bind.execute(
        sa.select(roles.c.id).where(roles.c.code == "administrator", roles.c.is_deleted.is_(False))
    ).all():
        existing = bind.execute(
            sa.select(role_permissions.c.id).where(
                role_permissions.c.role_id == role_id,
                role_permissions.c.permission_id == permission_id,
            )
        ).scalar_one_or_none()
        if existing is None:
            bind.execute(
                sa.insert(role_permissions).values(
                    id=_bind_uuid(bind, uuid.uuid4()),
                    created_at=now,
                    updated_at=now,
                    deleted_at=None,
                    is_deleted=False,
                    version=1,
                    role_id=_bind_uuid(bind, role_id),
                    permission_id=_bind_uuid(bind, permission_id),
                )
            )
        else:
            bind.execute(
                sa.update(role_permissions)
                .where(role_permissions.c.id == existing)
                .values(is_deleted=False, deleted_at=None, updated_at=now)
            )


def upgrade() -> None:
    _scope_workflow_rules()
    _scope_catalog(
        "expense_categories",
        "category_id",
        "code",
        "uq_expense_categories_code",
        "uq_expense_categories_organization_code",
    )
    _scope_catalog(
        "vendors",
        "vendor_id",
        "normalized_name",
        "uq_vendors_normalized_name",
        "uq_vendors_organization_normalized_name",
    )
    _add_notification_delivery_state()
    _create_outbox()
    _add_access_request_permission()


def _drop_scope(table_name: str, column_name: str, scoped_unique: str, old_unique: str) -> None:
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.drop_constraint(scoped_unique, type_="unique")
        batch_op.drop_constraint(f"fk_{table_name}_organization_id_organizations", type_="foreignkey")
        batch_op.create_unique_constraint(old_unique, [column_name])
        batch_op.drop_column("organization_id")
    op.drop_index(f"ix_{table_name}_organization_id", table_name=table_name)


def downgrade() -> None:
    op.drop_table("integration_outbox")
    op.drop_index("ix_notifications_delivery_lease", table_name="notifications")
    op.drop_index("ix_notifications_delivery_ready", table_name="notifications")
    with op.batch_alter_table("notifications") as batch_op:
        batch_op.drop_column("delivery_lease_expires_at")
        batch_op.drop_column("delivery_claimed_at")
        batch_op.drop_column("delivery_claim_token")
        batch_op.drop_column("next_attempt_at")
        batch_op.drop_column("delivery_attempts")
    _drop_scope("vendors", "normalized_name", "uq_vendors_organization_normalized_name", "uq_vendors_normalized_name")
    _drop_scope("expense_categories", "code", "uq_expense_categories_organization_code", "uq_expense_categories_code")
    op.drop_index("ix_workflow_rules_organization_id", table_name="workflow_rules")
    with op.batch_alter_table("workflow_rules") as batch_op:
        batch_op.drop_index("ix_workflow_rules_organization_priority_active")
        batch_op.drop_constraint("uq_workflow_rules_organization_name", type_="unique")
        batch_op.drop_constraint("fk_workflow_rules_organization_id_organizations", type_="foreignkey")
        batch_op.create_unique_constraint("uq_workflow_rules_name", ["name"])
        batch_op.drop_column("organization_id")
