"""Fresh-database migration regression coverage.

ORM metadata tests cannot prove that the Alembic artifacts deployed to a new
environment are valid, especially on SQLite's limited ALTER TABLE support.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import uuid

from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, Table, create_engine, inspect, select, text


def test_fresh_sqlite_database_upgrades_to_current_head(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "fresh-migrations.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{database_path}")
    backend_root = Path(__file__).resolve().parents[1]
    config = Config(str(backend_root / "alembic.ini"))

    command.upgrade(config, "head")

    engine = create_engine(f"sqlite+pysqlite:///{database_path}")
    try:
        inspector = inspect(engine)
        assert {"workflow_rules", "integration_outbox", "notifications"} <= set(inspector.get_table_names())
        assert "organization_id" in {column["name"] for column in inspector.get_columns("workflow_rules")}
        assert "organization_id" in {column["name"] for column in inspector.get_columns("expense_categories")}
        assert "delivery_lease_expires_at" in {
            column["name"] for column in inspector.get_columns("notifications")
        }
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
                "009_tenant_workflows_outbox"
            )
    finally:
        engine.dispose()


def test_ambiguous_legacy_catalog_is_quarantined_even_with_one_active_organization(
    tmp_path, monkeypatch
) -> None:
    """Never grant a formerly shared category to the only active tenant."""

    database_path = tmp_path / "ambiguous-catalog.sqlite"
    database_url = f"sqlite+pysqlite:///{database_path}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    backend_root = Path(__file__).resolve().parents[1]
    config = Config(str(backend_root / "alembic.ini"))
    command.upgrade(config, "008_email_auth_approval")

    # Reflected SQLite UUID columns are raw strings, unlike mapped Uuid
    # columns, so use the storage representation for this migration fixture.
    active_org_id = str(uuid.uuid4())
    inactive_org_id = str(uuid.uuid4())
    category_id = str(uuid.uuid4())
    active_policy_id = str(uuid.uuid4())
    inactive_policy_id = str(uuid.uuid4())
    engine = create_engine(database_url)
    try:
        metadata = MetaData()
        organizations = Table("organizations", metadata, autoload_with=engine)
        categories = Table("expense_categories", metadata, autoload_with=engine)
        policies = Table("policies", metadata, autoload_with=engine)
        policy_rules = Table("policy_rules", metadata, autoload_with=engine)
        now = datetime.now(UTC)
        with engine.begin() as connection:
            connection.execute(
                organizations.insert(),
                [
                    {
                        "id": active_org_id,
                        "name": "Active tenant",
                        "code": "ACTIVE",
                        "base_currency": "USD",
                        "status": "active",
                    },
                    {
                        "id": inactive_org_id,
                        "name": "Inactive historical tenant",
                        "code": "INACTIVE",
                        "base_currency": "USD",
                        "status": "inactive",
                    },
                ],
            )
            connection.execute(
                categories.insert().values(id=category_id, code="SHARED", name="Shared historical category")
            )
            connection.execute(
                policies.insert(),
                [
                    {
                        "id": active_policy_id,
                        "organization_id": active_org_id,
                        "name": "Active policy",
                        "version_label": "v1",
                        "effective_from": now,
                    },
                    {
                        "id": inactive_policy_id,
                        "organization_id": inactive_org_id,
                        "name": "Inactive policy",
                        "version_label": "v1",
                        "effective_from": now,
                    },
                ],
            )
            connection.execute(
                policy_rules.insert(),
                [
                    {"id": str(uuid.uuid4()), "policy_id": active_policy_id, "category_id": category_id},
                    {"id": str(uuid.uuid4()), "policy_id": inactive_policy_id, "category_id": category_id},
                ],
            )
    finally:
        engine.dispose()

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    try:
        metadata = MetaData()
        organizations = Table("organizations", metadata, autoload_with=engine)
        categories = Table("expense_categories", metadata, autoload_with=engine)
        with engine.connect() as connection:
            assigned_organization_id = connection.execute(
                select(categories.c.organization_id).where(categories.c.id == category_id)
            ).scalar_one()
            assigned = connection.execute(
                select(organizations.c.code, organizations.c.status).where(
                    organizations.c.id == assigned_organization_id
                )
            ).one()
        assert assigned_organization_id not in {active_org_id, inactive_org_id}
        assert assigned.code.startswith("LEGACY-DOMAIN-QUARANTINE")
        assert assigned.status == "inactive"
    finally:
        engine.dispose()
