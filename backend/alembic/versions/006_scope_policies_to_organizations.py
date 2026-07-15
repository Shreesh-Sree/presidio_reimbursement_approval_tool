"""Scope reimbursement policies to a single organization.

Revision ID: 006_scope_policies_to_organizations
Revises: 005_delegated_approvals
Create Date: 2026-07-15

Historical policy rows did not record an organization or creator.  This
migration first derives ownership only when the evidence is unambiguous: a
policy's creating audit actor and every report that applied the policy must
resolve to one organization.  If there is no evidence, or the evidence spans
organizations, the row is moved into an inactive, userless quarantine
organization rather than guessed into a tenant.  Administrators can then
recreate or explicitly migrate that legacy policy with an audited deployment
procedure; no tenant can read a policy whose ownership is unknown.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
import uuid

from alembic import op
import sqlalchemy as sa


revision = "006_scope_policies_to_organizations"
down_revision = "005_delegated_approvals"
branch_labels = None
depends_on = None


_QUARANTINE_CODE_PREFIX = "LEGACY-POLICY-QUARANTINE"


def _key(value: object) -> str:
    """Normalize reflected UUID/string values for portable SQLite/PostgreSQL reads."""

    return str(value)


def _bind_uuid(bind, value: object) -> object:
    """Preserve native UUID values on PostgreSQL and text-bind on SQLite."""

    return _key(value) if bind.dialect.name == "sqlite" else value


def _new_quarantine_organization(bind, organizations: sa.Table) -> object:
    """Create a userless inactive tenant for ambiguous legacy policy ownership."""

    existing_codes = {
        str(code)
        for (code,) in bind.execute(sa.select(organizations.c.code)).all()
        if code is not None
    }
    code = _QUARANTINE_CODE_PREFIX
    suffix = 2
    while code in existing_codes:
        code = f"{_QUARANTINE_CODE_PREFIX[:45]}-{suffix}"
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
            name="Legacy Policy Quarantine",
            code=code,
            base_currency="INR",
            status="inactive",
        )
    )
    return organization_id


def _backfill_policy_organizations(bind, policies: sa.Table) -> None:
    """Assign existing rows without ever using a cross-tenant guess."""

    metadata = sa.MetaData()
    organizations = sa.Table("organizations", metadata, autoload_with=bind)
    users = sa.Table("users", metadata, autoload_with=bind)
    reports = sa.Table("expense_reports", metadata, autoload_with=bind)
    audit_logs = sa.Table("audit_logs", metadata, autoload_with=bind)

    user_organizations = {
        _key(user_id): organization_id
        for user_id, organization_id in bind.execute(
            sa.select(users.c.id, users.c.organization_id)
        ).all()
        if organization_id is not None
    }
    candidates: dict[str, set[object]] = defaultdict(set)

    # An old audit row can identify the creator, when the legacy service did
    # capture an actor.  Only creation records count as ownership evidence.
    for record_id, performed_by in bind.execute(
        sa.select(audit_logs.c.record_id, audit_logs.c.performed_by).where(
            audit_logs.c.entity_name == "policies",
            audit_logs.c.operation.in_(("create", "insert")),
        )
    ).all():
        organization_id = user_organizations.get(_key(performed_by)) if performed_by else None
        if organization_id is not None:
            candidates[_key(record_id)].add(organization_id)

    # Submitted reports provide a second conservative source.  A policy that
    # was historically used by more than one organization is deliberately not
    # assigned to either of them.
    report_rows = bind.execute(
        sa.select(reports.c.applied_policy_id, users.c.organization_id)
        .select_from(reports.join(users, reports.c.employee_user_id == users.c.id))
        .where(reports.c.applied_policy_id.is_not(None))
    ).all()
    for policy_id, organization_id in report_rows:
        if policy_id is not None and organization_id is not None:
            candidates[_key(policy_id)].add(organization_id)

    active_organizations = [
        organization_id
        for organization_id, is_deleted in bind.execute(
            sa.select(organizations.c.id, organizations.c.is_deleted)
        ).all()
        if not is_deleted
    ]
    single_tenant_id = active_organizations[0] if len(active_organizations) == 1 else None

    unresolved: list[object] = []
    for (policy_id,) in bind.execute(
        sa.select(policies.c.id).where(policies.c.organization_id.is_(None))
    ).all():
        policy_candidates = candidates.get(_key(policy_id), set())
        if len(policy_candidates) == 1:
            organization_id = next(iter(policy_candidates))
        elif single_tenant_id is not None:
            # A single active organization is unambiguous even if the legacy
            # data predates audit/report references.
            organization_id = single_tenant_id
        else:
            unresolved.append(policy_id)
            continue
        bind.execute(
            sa.update(policies)
            .where(policies.c.id == policy_id)
            .values(organization_id=_bind_uuid(bind, organization_id))
        )

    if unresolved:
        quarantine_id = _new_quarantine_organization(bind, organizations)
        for policy_id in unresolved:
            bind.execute(
                sa.update(policies)
                .where(policies.c.id == policy_id)
                .values(organization_id=_bind_uuid(bind, quarantine_id))
            )


def upgrade() -> None:
    # Nullable during backfill avoids inventing a tenant while the database is
    # in transition.  The batch operation below makes it required afterwards.
    op.add_column("policies", sa.Column("organization_id", sa.Uuid(as_uuid=True), nullable=True))
    metadata = sa.MetaData()
    policies = sa.Table("policies", metadata, autoload_with=op.get_bind())
    _backfill_policy_organizations(op.get_bind(), policies)

    # Batch mode keeps the migration verifiable against SQLite while PostgreSQL
    # emits the corresponding ALTER statements.
    with op.batch_alter_table("policies") as batch_op:
        batch_op.drop_constraint("uq_policies_name_version", type_="unique")
        batch_op.alter_column(
            "organization_id",
            existing_type=sa.Uuid(as_uuid=True),
            nullable=False,
        )
        batch_op.create_foreign_key(
            "fk_policies_organization_id_organizations",
            "organizations",
            ["organization_id"],
            ["id"],
        )
        batch_op.create_unique_constraint(
            "uq_policies_organization_name_version",
            ["organization_id", "name", "version_label"],
        )
        batch_op.create_index("ix_policies_organization_id", ["organization_id"])
        batch_op.create_index("ix_policies_organization_active", ["organization_id", "is_active"])


def downgrade() -> None:
    bind = op.get_bind()
    metadata = sa.MetaData()
    policies = sa.Table("policies", metadata, autoload_with=bind)
    duplicate = bind.execute(
        sa.select(policies.c.name, policies.c.version_label)
        .group_by(policies.c.name, policies.c.version_label)
        .having(sa.func.count() > 1)
        .limit(1)
    ).first()
    if duplicate is not None:
        raise RuntimeError(
            "Cannot safely downgrade policy tenant scope while policy name/version "
            "pairs exist in more than one organization."
        )

    with op.batch_alter_table("policies") as batch_op:
        batch_op.drop_index("ix_policies_organization_active")
        batch_op.drop_index("ix_policies_organization_id")
        batch_op.drop_constraint("uq_policies_organization_name_version", type_="unique")
        batch_op.drop_constraint("fk_policies_organization_id_organizations", type_="foreignkey")
        batch_op.create_unique_constraint("uq_policies_name_version", ["name", "version_label"])
        batch_op.drop_column("organization_id")
