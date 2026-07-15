"""Shared, isolated test database and API fixtures.

The application uses PostgreSQL in production.  Tests deliberately use one
in-memory SQLite connection so they are fast, deterministic, and do not need a
developer database.  Models use SQLAlchemy's portable ``Uuid`` type, so this
also exercises the same mappings used by PostgreSQL.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

# Settings are read during app imports, so set safe test defaults first.
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "a-very-long-secret-key-for-testing-at-least-32-bytes-long-definitely")
os.environ.setdefault("S3_BUCKET", "test-bucket")

import app.models  # noqa: E402,F401 - registers every mapped table with Base
from app.core.database import Base, get_db  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.expense_category import ExpenseCategory  # noqa: E402
from app.models.organization import Organization  # noqa: E402
from app.models.policy import Policy  # noqa: E402
from app.models.user import User  # noqa: E402


@pytest.fixture()
def engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def db(engine):
    session = Session(engine)
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def client(engine):
    from app.main import app

    def override_get_db():
        session = Session(engine)
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def seeded_org(db):
    organization = Organization(name="Presidio Test", code="PRESIDIO", base_currency="USD")
    db.add(organization)
    db.flush()
    return organization


@pytest.fixture()
def seeded_department(db, seeded_org):
    department = Department(organization_id=seeded_org.id, code="ENG", name="Engineering")
    db.add(department)
    db.flush()
    return department


@pytest.fixture()
def seeded_user(db, seeded_org, seeded_department):
    user = User(
        organization_id=seeded_org.id,
        department_id=seeded_department.id,
        employee_number="E-001",
        username="employee",
        email="employee@example.com",
        password_hash=hash_password("correct-horse-battery-staple"),
        full_name="Test Employee",
        status="active",
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture()
def seeded_policy(db):
    policy = Policy(
        name="Travel policy",
        version_label="v1",
        is_active=True,
        effective_from=datetime.now(UTC) - timedelta(days=1),
    )
    db.add(policy)
    db.flush()
    return policy


@pytest.fixture()
def seeded_category(db):
    category = ExpenseCategory(code="TRAVEL", name="Travel", receipt_required=True)
    db.add(category)
    db.flush()
    return category
