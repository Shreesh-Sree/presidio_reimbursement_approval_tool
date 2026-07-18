#!/usr/bin/env python3
"""
Seed database with sample data for testing.
Run: uv run python seed_data.py
"""
import asyncio
from datetime import datetime, timedelta, UTC
from decimal import Decimal

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.core.config import get_settings
from app.models import (
    Organization,
    Department,
    User,
    ExpenseCategory,
    Policy,
    ExpenseReport,
    ExpenseItem,
)


async def seed_database():
    """Seed database with sample data."""
    engine = create_async_engine(get_settings().database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Check if data already exists
        result = await session.execute(select(Organization))
        if result.scalars().first():
            print("✓ Data already seeded. Skipping.")
            return

        print("Seeding database...")

        # 1. Organization
        org = Organization(
            name="Presidio Demo Corp",
            code="PRESIDIO",
            description="Demo organization for testing",
        )
        session.add(org)
        await session.flush()

        # 2. Departments
        departments = [
            Department(name="Engineering", code="ENG", organization_id=org.id),
            Department(name="Sales", code="SALES", organization_id=org.id),
            Department(name="Marketing", code="MKT", organization_id=org.id),
        ]
        session.add_all(departments)
        await session.flush()

        eng_dept = departments[0]

        # 3. Users
        users = [
            User(
                email="admin@presidio.demo",
                full_name="Admin User",
                organization_id=org.id,
                department_id=eng_dept.id,
                is_active=True,
            ),
            User(
                email="manager@presidio.demo",
                full_name="Manager Smith",
                organization_id=org.id,
                department_id=eng_dept.id,
                is_active=True,
            ),
            User(
                email="employee@presidio.demo",
                full_name="Employee Jones",
                organization_id=org.id,
                department_id=eng_dept.id,
                is_active=True,
            ),
        ]
        session.add_all(users)
        await session.flush()

        admin, manager, employee = users
        manager.manager_id = admin.id
        employee.manager_id = manager.id

        # 4. Expense Categories
        categories = [
            ExpenseCategory(
                name="Travel",
                code="TRAVEL",
                description="Travel expenses",
                organization_id=org.id,
                is_active=True,
            ),
            ExpenseCategory(
                name="Meals",
                code="MEALS",
                description="Meal expenses",
                organization_id=org.id,
                is_active=True,
            ),
            ExpenseCategory(
                name="Office Supplies",
                code="SUPPLIES",
                description="Office supplies",
                organization_id=org.id,
                is_active=True,
            ),
        ]
        session.add_all(categories)
        await session.flush()

        travel_cat, meals_cat, supplies_cat = categories

        # 5. Policies
        policies = [
            Policy(
                name="Meal Policy",
                description="Maximum $50 per meal",
                category_id=meals_cat.id,
                organization_id=org.id,
                max_amount=Decimal("50.00"),
                requires_receipt=True,
                is_active=True,
            ),
            Policy(
                name="Travel Policy",
                description="Flight and hotel expenses",
                category_id=travel_cat.id,
                organization_id=org.id,
                max_amount=Decimal("2000.00"),
                requires_receipt=True,
                is_active=True,
            ),
        ]
        session.add_all(policies)
        await session.flush()

        # 6. Sample Reports
        today = datetime.now(UTC)
        reports = [
            ExpenseReport(
                user_id=employee.id,
                title="Team Lunch - Q3 Planning",
                description="Team lunch for Q3 planning meeting",
                total_amount=Decimal("85.50"),
                status="pending",
                created_at=today - timedelta(days=2),
            ),
            ExpenseReport(
                user_id=employee.id,
                title="Client Visit Travel",
                description="Flight and hotel for client visit",
                total_amount=Decimal("1250.00"),
                status="pending",
                created_at=today - timedelta(days=5),
            ),
            ExpenseReport(
                user_id=manager.id,
                title="Office Supplies",
                description="Monthly office supplies",
                total_amount=Decimal("150.00"),
                status="approved",
                created_at=today - timedelta(days=10),
            ),
        ]
        session.add_all(reports)
        await session.flush()

        report1, report2, report3 = reports

        # 7. Report Items
        items = [
            # Report 1 items
            ExpenseItem(
                report_id=report1.id,
                category_id=meals_cat.id,
                description="Team lunch at Italian restaurant",
                amount=Decimal("85.50"),
                expense_date=today - timedelta(days=2),
            ),
            # Report 2 items
            ExpenseItem(
                report_id=report2.id,
                category_id=travel_cat.id,
                description="Round-trip flight to NYC",
                amount=Decimal("450.00"),
                expense_date=today - timedelta(days=5),
            ),
            ExpenseItem(
                report_id=report2.id,
                category_id=travel_cat.id,
                description="Hotel - 3 nights",
                amount=Decimal("800.00"),
                expense_date=today - timedelta(days=5),
            ),
            # Report 3 items
            ExpenseItem(
                report_id=report3.id,
                category_id=supplies_cat.id,
                description="Printer paper and pens",
                amount=Decimal("150.00"),
                expense_date=today - timedelta(days=10),
            ),
        ]
        session.add_all(items)

        await session.commit()
        print("✓ Database seeded successfully!")
        print(f"  - 1 organization")
        print(f"  - {len(departments)} departments")
        print(f"  - {len(users)} users")
        print(f"  - {len(categories)} expense categories")
        print(f"  - {len(policies)} policies")
        print(f"  - {len(reports)} reports")
        print(f"  - {len(items)} report items")


async def main():
    try:
        await seed_database()
    except Exception as e:
        print(f"Error seeding database: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())
