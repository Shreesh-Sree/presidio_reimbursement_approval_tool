"""Seed the demo database with 4 users, policies, reports, and full lifecycle data.

Usage (from repo root):
    DATABASE_URL=postgresql://user:pass@host/db python scripts/seed_demo.py --wipe

Or inside backend venv:
    cd backend && uv run python ../scripts/seed_demo.py --wipe --assets-dir ../scripts/demo_assets
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
os.environ.setdefault("DEPLOYMENT_ENVIRONMENT", "local")
os.environ.setdefault("JWT_SECRET", "seed-placeholder")

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.models import (
    ApprovalHistory,
    ApprovalLevel,
    Attachment,
    Comment,
    Department,
    ExpenseCategory,
    ExpenseItem,
    ExpenseReport,
    Notification,
    Organization,
    PaymentRecord,
    Permission,
    Policy,
    PolicyRule,
    Role,
    RolePermission,
    User,
    UserRole,
    Vendor,
    WorkflowRule,
)
from app.services import user_service


TABLES_TO_TRUNCATE = [
    "payment_events", "payment_records", "payment_batches",
    "comments", "notifications", "approval_history", "approval_levels",
    "attachments", "expense_items", "expense_reports",
    "integration_outbox", "delegations", "sessions",
    "user_access_requests", "audit_logs",
    "policy_rules", "policies",
    "workflow_rules", "vendors", "expense_categories",
    "user_roles", "role_permissions", "users",
    "permissions", "roles", "departments", "organizations",
]

DEMO_USERS = [
    {"email": "shreesh.exe22@gmail.com", "full_name": "Shreesh Kumar", "roles": ["administrator"], "dept": "ENGINEERING"},
    {"email": "algoqx@gmail.com", "full_name": "Algo Manager", "roles": ["approver"], "dept": "ENGINEERING"},
    {"email": "svaimitra@gmail.com", "full_name": "Svai Mitra", "roles": ["finance"], "dept": "FINANCE"},
    {"email": "quarkverse.canva@gmail.com", "full_name": "Quark Verse", "roles": ["employee"], "dept": "ENGINEERING"},
]

CATEGORIES = [
    ("MEALS", "Meals & Dining"),
    ("TRAVEL_AIR", "Air Travel"),
    ("TRAVEL_TRAIN", "Train Travel"),
    ("TRAVEL_TAXI", "Taxi / Cab"),
    ("HOTEL", "Hotel / Accommodation"),
    ("OFFICE_SUPPLIES", "Office Supplies"),
    ("COMMUTE", "Daily Commute"),
    ("CONFERENCE", "Conference & Events"),
    ("MISCELLANEOUS", "Miscellaneous"),
]

VENDORS_LIST = [
    "Uber India", "Ola Cabs", "IndiGo Airlines", "Air India",
    "Taj Hotels", "OYO Rooms", "Dominos", "Swiggy",
    "Amazon India", "Flipkart", "IRCTC",
]


def wipe_database(engine) -> None:
    print("Wiping database...")
    with engine.connect() as conn:
        conn.execute(text("SET session_replication_role = 'replica'"))
        for table in TABLES_TO_TRUNCATE:
            try:
                conn.execute(text(f'TRUNCATE TABLE "{table}" CASCADE'))
            except Exception:
                pass
        conn.execute(text("SET session_replication_role = 'origin'"))
        conn.commit()
    print("  All tables truncated.")


def seed_org(db: Session) -> Organization:
    org = Organization(name="Presidio", code="PRESIDIO", base_currency="INR", status="active")
    db.add(org)
    db.flush()
    print(f"  Organization: {org.name} ({org.id})")
    return org


def seed_departments(db: Session, org: Organization) -> dict[str, Department]:
    depts: dict[str, Department] = {}
    for code, name in [("ENGINEERING", "Engineering"), ("FINANCE", "Finance"), ("SALES", "Sales"), ("GENERAL", "General")]:
        d = Department(organization_id=org.id, code=code, name=name, status="active")
        db.add(d)
        depts[code] = d
    db.flush()
    print(f"  Departments: {list(depts.keys())}")
    return depts


def seed_users(db: Session, org: Organization, depts: dict[str, Department]) -> dict[str, User]:
    user_service.ensure_system_roles_and_permissions(db)
    db.commit()
    print("  System roles/permissions seeded.")

    users: dict[str, User] = {}
    for spec in DEMO_USERS:
        result = user_service.create_user(
            db,
            organization_id=org.id,
            department_id=depts[spec["dept"]].id,
            email=spec["email"],
            full_name=spec["full_name"],
            role_codes=spec["roles"],
            manager_id=None,
        )
        user = db.get(User, uuid.UUID(str(result["id"])))
        users[spec["email"]] = user
        print(f"    User: {spec['email']} ({spec['roles'][0]})")

    employee = users["quarkverse.canva@gmail.com"]
    manager = users["algoqx@gmail.com"]
    admin = users["shreesh.exe22@gmail.com"]
    employee.manager_user_id = manager.id
    manager.manager_user_id = admin.id
    db.commit()
    return users


def seed_categories(db: Session, org: Organization) -> dict[str, ExpenseCategory]:
    cats: dict[str, ExpenseCategory] = {}
    for code, name in CATEGORIES:
        c = ExpenseCategory(organization_id=org.id, code=code, name=name, receipt_required=True)
        db.add(c)
        cats[code] = c
    db.flush()
    db.commit()
    print(f"  Categories: {len(cats)}")
    return cats


def seed_vendors(db: Session, org: Organization) -> dict[str, Vendor]:
    vendors: dict[str, Vendor] = {}
    for name in VENDORS_LIST:
        v = Vendor(organization_id=org.id, name=name, normalized_name=name.lower().strip())
        db.add(v)
        vendors[name] = v
    db.flush()
    db.commit()
    print(f"  Vendors: {len(vendors)}")
    return vendors


def seed_policies(db: Session, org: Organization, cats: dict[str, ExpenseCategory], assets_dir: Path, admin_id: uuid.UUID) -> Policy:
    policy = Policy(
        organization_id=org.id,
        name="Presidio Travel & Expense Policy",
        version_label="v2.0",
        is_active=True,
        effective_from=datetime(2026, 1, 1, tzinfo=UTC),
    )
    db.add(policy)
    db.flush()

    rules_spec = [
        ("MEALS", 2000, None, None, 500),
        ("TRAVEL_AIR", None, 25000, None, 0),
        ("TRAVEL_TRAIN", None, 5000, None, 0),
        ("TRAVEL_TAXI", 3000, None, None, 200),
        ("HOTEL", 10000, None, None, 0),
        ("OFFICE_SUPPLIES", None, None, 5000, 500),
        ("COMMUTE", 1500, None, None, 1000),
        ("CONFERENCE", None, 50000, None, 0),
        ("MISCELLANEOUS", None, 3000, None, 500),
    ]
    for cat_code, per_day, per_trip, cap, receipt_above in rules_spec:
        rule = PolicyRule(
            policy_id=policy.id,
            category_id=cats[cat_code].id,
            max_per_day=Decimal(str(per_day)) if per_day else Decimal("0"),
            max_per_trip=Decimal(str(per_trip)) if per_trip else Decimal("0"),
            per_category_cap=Decimal(str(cap)) if cap else Decimal("0"),
            receipt_required_above=Decimal(str(receipt_above)),
        )
        db.add(rule)
    db.flush()

    for pdf_name in ["travel_policy.pdf", "expense_limits_policy.pdf", "receipt_requirements_policy.pdf"]:
        pdf_path = assets_dir / pdf_name
        if pdf_path.exists():
            content = pdf_path.read_bytes()
            att = Attachment(
                entity_type="policy_document",
                entity_id=policy.id,
                file_name=pdf_name,
                original_file_name=pdf_name,
                storage_path=f"local://policies/{policy.id}/{pdf_name}",
                mime_type="application/pdf",
                file_size_bytes=len(content),
                checksum=hashlib.sha256(content).hexdigest(),
                uploaded_by=admin_id,
            )
            db.add(att)
            local_dir = Path(".local-storage") / "policies" / str(policy.id)
            local_dir.mkdir(parents=True, exist_ok=True)
            (local_dir / pdf_name).write_bytes(content)

    policy.uploaded_document_attachment_id = att.id if "att" in dir() else None
    db.commit()
    print(f"  Policy: {policy.name} (active, {len(rules_spec)} rules)")
    return policy


def seed_workflows(db: Session, org: Organization) -> None:
    r1 = WorkflowRule(
        organization_id=org.id,
        name="Default Manager Approval",
        conditions_json={"min_amount": 0},
        approval_chain_json=[{"type": "manager", "level": 1}],
        priority=100,
        is_active=True,
    )
    r2 = WorkflowRule(
        organization_id=org.id,
        name="High Value Finance Review",
        conditions_json={"min_amount": 10000},
        approval_chain_json=[{"type": "manager", "level": 1}, {"type": "role", "role_code": "finance", "level": 2}],
        priority=50,
        is_active=True,
    )
    db.add_all([r1, r2])
    db.commit()
    print("  Workflow rules: 2")


def _report_number() -> str:
    return f"RPT-{uuid.uuid4().hex[:12].upper()}"


def _attach_receipt(db: Session, item: ExpenseItem, receipt_file: Path, uploader_id: uuid.UUID) -> None:
    if not receipt_file.exists():
        return
    content = receipt_file.read_bytes()
    mime = "application/pdf" if receipt_file.suffix == ".pdf" else "image/png"
    key = f"receipts/{item.expense_report_id}/{item.id}/{receipt_file.name}"
    att = Attachment(
        entity_type="expense_item_receipt",
        entity_id=item.id,
        file_name=receipt_file.name,
        original_file_name=receipt_file.name,
        storage_path=f"local://{key}",
        mime_type=mime,
        file_size_bytes=len(content),
        checksum=hashlib.sha256(content).hexdigest(),
        uploaded_by=uploader_id,
    )
    db.add(att)
    local_path = Path(".local-storage") / key
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(content)


def seed_reports(
    db: Session,
    users: dict[str, User],
    cats: dict[str, ExpenseCategory],
    vendors: dict[str, Vendor],
    policy: Policy,
    assets_dir: Path,
) -> None:
    employee = users["quarkverse.canva@gmail.com"]
    manager = users["algoqx@gmail.com"]
    finance = users["svaimitra@gmail.com"]

    today = date.today()

    scenarios = [
        # (submitter, title, status, days_ago, items: [(cat, amount, desc, receipt_file)])
        (employee, "Bangalore Client Visit - June", "paid", 30, [
            ("TRAVEL_TAXI", 501, "Uber to Airport", "receipt_uber_001.png"),
            ("TRAVEL_AIR", 4778, "IndiGo BLR-DEL", "receipt_indigo_blr_del.pdf"),
            ("HOTEL", 17528, "Taj Bangalore 2N", "receipt_taj_blr.pdf"),
            ("MEALS", 778, "Team Lunch Dominos", "receipt_dominos_001.png"),
            ("TRAVEL_TAXI", 429, "Ola to Client", "receipt_ola_001.png"),
        ]),
        (employee, "Mumbai Conference Trip", "approved_pending_payment", 20, [
            ("TRAVEL_AIR", 5933, "Air India DEL-BOM", "receipt_airindia_del_bom.pdf"),
            ("HOTEL", 3696, "OYO Pune 1N", "receipt_oyo_pune.pdf"),
            ("MEALS", 2365, "Team Lunch Swiggy", "receipt_swiggy_001.png"),
            ("TRAVEL_TAXI", 501, "Uber to Hotel", "receipt_uber_001.png"),
        ]),
        (employee, "Weekly Commute June W1", "approved", 15, [
            ("COMMUTE", 1500, "Namma Metro Monthly", "receipt_metro_001.png"),
            ("COMMUTE", 250, "BMTC Bus Pass", "receipt_bus_001.png"),
        ]),
        (employee, "Sprint Review Team Lunch", "submitted", 5, [
            ("MEALS", 2365, "Swiggy Dineout - Team", "receipt_swiggy_001.png"),
            ("MEALS", 480, "Chai Point Office", "receipt_chai_001.png"),
        ]),
        (employee, "Office Supplies Q2", "draft", 2, [
            ("OFFICE_SUPPLIES", 2547, "Amazon - Mouse + Hub", "receipt_amazon_001.png"),
            ("OFFICE_SUPPLIES", 2198, "Flipkart Monitor Stand", "receipt_flipkart_001.png"),
        ]),
        (employee, "Delhi Sales Meeting", "paid", 45, [
            ("TRAVEL_AIR", 4778, "IndiGo BLR-DEL", "receipt_indigo_blr_del.pdf"),
            ("HOTEL", 11872, "Lemon Tree Chennai 2N", "receipt_lemontree_chn.pdf"),
            ("MEALS", 5635, "Client Dinner Acme", "receipt_dinner_client_001.png"),
            ("TRAVEL_TAXI", 429, "Ola Rides", "receipt_ola_001.png"),
        ]),
        (employee, "Pune Workshop Travel", "rejected", 25, [
            ("TRAVEL_TRAIN", 970, "Shatabdi BLR-MYS", "receipt_irctc_blr_mys.pdf"),
            ("HOTEL", 3696, "OYO Pune", "receipt_oyo_pune.pdf"),
            ("MEALS", 2365, "Team Dinner", "receipt_swiggy_001.png"),
        ]),
        (employee, "April Commute Reimbursement", "paid", 60, [
            ("COMMUTE", 1500, "Metro Pass April", "receipt_metro_001.png"),
            ("COMMUTE", 250, "Bus Pass April", "receipt_bus_001.png"),
            ("TRAVEL_TAXI", 85, "Rapido Bike Ride", "receipt_rapido_001.png"),
        ]),
        (employee, "Tech Summit Registration", "sent_back", 10, [
            ("CONFERENCE", 35400, "TechSummit India 2026", "receipt_techsummit_reg.pdf"),
            ("OFFICE_SUPPLIES", 18996, "Conference Supplies Amazon", "receipt_amazon_conf.pdf"),
        ]),
        (employee, "Client Dinner - Acme Corp", "submitted", 7, [
            ("MEALS", 5635, "Restaurant Bangalore", "receipt_dinner_client_001.png"),
            ("TRAVEL_TAXI", 501, "Uber to Restaurant", "receipt_uber_001.png"),
        ]),
        (employee, "Airport Taxi Claims", "paid", 35, [
            ("TRAVEL_TAXI", 501, "Uber Airport", "receipt_uber_001.png"),
            ("TRAVEL_TAXI", 429, "Ola Return", "receipt_ola_001.png"),
        ]),
        (employee, "Stationery Purchase", "approved_pending_payment", 12, [
            ("OFFICE_SUPPLIES", 2547, "Amazon Supplies", "receipt_amazon_001.png"),
        ]),
        # Manager's own reports
        (manager, "Quarterly Review Travel", "paid", 40, [
            ("TRAVEL_AIR", 4095, "SpiceJet BLR-HYD", "receipt_spicejet_blr_hyd.pdf"),
            ("HOTEL", 11872, "Lemon Tree Chennai", "receipt_lemontree_chn.pdf"),
            ("MEALS", 2365, "Team Dinner", "receipt_swiggy_001.png"),
        ]),
        (manager, "Team Building Dinner", "approved_pending_payment", 18, [
            ("MEALS", 5635, "Client Restaurant", "receipt_dinner_client_001.png"),
            ("TRAVEL_TAXI", 501, "Uber Rides", "receipt_uber_001.png"),
        ]),
        (manager, "Hiring Trip Chennai", "submitted", 8, [
            ("TRAVEL_AIR", 5933, "Air India Flight", "receipt_airindia_del_bom.pdf"),
            ("HOTEL", 3696, "OYO Chennai", "receipt_oyo_pune.pdf"),
        ]),
    ]

    admin = users["shreesh.exe22@gmail.com"]
    report_count = 0

    for submitter, title, target_status, days_ago, items_spec in scenarios:
        report = ExpenseReport(
            report_number=_report_number(),
            employee_user_id=submitter.id,
            department_id=submitter.department_id,
            applied_policy_id=policy.id,
            title=title,
            start_date=today - timedelta(days=days_ago + 2),
            end_date=today - timedelta(days=days_ago),
            currency_code="INR",
            status="draft",
            total_amount=Decimal("0"),
        )
        db.add(report)
        db.flush()

        total = Decimal("0")
        for idx, (cat_code, amount, desc, receipt_name) in enumerate(items_spec, 1):
            item = ExpenseItem(
                expense_report_id=report.id,
                line_number=idx,
                category_id=cats[cat_code].id,
                merchant_name=desc.split(" - ")[0] if " - " in desc else desc[:30],
                amount=Decimal(str(amount)),
                expense_date=today - timedelta(days=days_ago + 2 - idx),
                description=desc,
                is_policy_violated=False,
            )
            db.add(item)
            db.flush()
            total += Decimal(str(amount))

            receipt_path = assets_dir / receipt_name
            _attach_receipt(db, item, receipt_path, submitter.id)

        report.total_amount = total

        if target_status == "draft":
            db.flush()
            report_count += 1
            continue

        report.status = "submitted"
        report.submitted_at = datetime.now(UTC) - timedelta(days=days_ago)

        approval_level = ApprovalLevel(
            expense_report_id=report.id,
            level_number=1,
            approver_user_id=manager.id if submitter != manager else admin.id,
            status="pending",
        )
        db.add(approval_level)
        db.flush()

        if target_status == "submitted":
            report_count += 1
            continue

        approver = manager if submitter != manager else admin
        performed_at = datetime.now(UTC) - timedelta(days=days_ago - 1)

        if target_status == "rejected":
            report.status = "rejected"
            approval_level.status = "rejected"
            ah = ApprovalHistory(
                expense_report_id=report.id,
                approval_level_id=approval_level.id,
                action="reject",
                performed_by=approver.id,
                performed_at=performed_at,
                remarks="Exceeds policy limits. Please revise and resubmit.",
            )
            db.add(ah)
            _add_comment(db, report.id, approver.id, "This report exceeds the daily hotel limit. Please split across policy-compliant stays.")
            report_count += 1
            continue

        if target_status == "sent_back":
            report.status = "sent_back"
            approval_level.status = "sent_back"
            ah = ApprovalHistory(
                expense_report_id=report.id,
                approval_level_id=approval_level.id,
                action="send_back",
                performed_by=approver.id,
                performed_at=performed_at,
                remarks="Missing receipts for conference items.",
            )
            db.add(ah)
            _add_comment(db, report.id, approver.id, "Please attach the original conference registration invoice and provide breakdown of supplies.")
            report_count += 1
            continue

        report.status = "approved"
        approval_level.status = "approved"
        ah = ApprovalHistory(
            expense_report_id=report.id,
            approval_level_id=approval_level.id,
            action="approve",
            performed_by=approver.id,
            performed_at=performed_at,
            remarks="Approved - all items within policy.",
        )
        db.add(ah)
        _add_comment(db, report.id, approver.id, "Looks good. Approved.")

        if target_status == "approved":
            report_count += 1
            continue

        report.status = "approved_pending_payment"
        payment = PaymentRecord(
            expense_report_id=report.id,
            payment_reference=f"PAY-{report.report_number}",
            amount=total,
            status="pending",
            processed_by=finance.id,
        )
        db.add(payment)
        db.flush()

        if target_status == "paid":
            report.status = "paid"
            payment.status = "completed"
            payment.payment_date = (today - timedelta(days=days_ago - 3))
            payment.provider_reference = f"NEFT-{uuid.uuid4().hex[:8].upper()}"
            payment.remarks = "Processed via NEFT to registered bank account."

        report_count += 1

    db.commit()
    print(f"  Reports: {report_count} (with items, approvals, payments)")


def _add_comment(db: Session, report_id: uuid.UUID, user_id: uuid.UUID, text: str) -> None:
    c = Comment(
        expense_report_id=report_id,
        author_user_id=user_id,
        visibility="public",
        text=text,
    )
    db.add(c)


def seed_notifications(db: Session, users: dict[str, User]) -> None:
    employee = users["quarkverse.canva@gmail.com"]
    manager = users["algoqx@gmail.com"]
    finance = users["svaimitra@gmail.com"]
    admin = users["shreesh.exe22@gmail.com"]

    notifications = [
        (manager.id, "report_submitted", {"title": "New Report Submitted", "body": "Quark Verse submitted 'Sprint Review Team Lunch' for approval."}),
        (manager.id, "report_submitted", {"title": "New Report Submitted", "body": "Quark Verse submitted 'Client Dinner - Acme Corp' for approval."}),
        (employee.id, "report_approved", {"title": "Report Approved", "body": "Your report 'Bangalore Client Visit' has been approved and sent for payment."}),
        (employee.id, "payment_processed", {"title": "Payment Processed", "body": "INR 23,515 has been transferred for 'Bangalore Client Visit' via NEFT."}),
        (employee.id, "report_rejected", {"title": "Report Returned", "body": "'Pune Workshop Travel' was rejected. Please review manager's comments."}),
        (employee.id, "report_sent_back", {"title": "Revisions Requested", "body": "'Tech Summit Registration' needs additional documentation. Check comments."}),
        (finance.id, "payment_pending", {"title": "Payments Awaiting", "body": "4 approved reports are pending payment processing."}),
        (admin.id, "system_info", {"title": "System Ready", "body": "All microservices are healthy. Policy assistant index contains 3 documents."}),
    ]

    for recipient_id, template, payload in notifications:
        n = Notification(
            recipient_user_id=recipient_id,
            template_code=template,
            channel="in_app",
            status="delivered",
            payload_json=payload,
            sent_at=datetime.now(UTC) - timedelta(hours=2),
        )
        db.add(n)
    db.commit()
    print(f"  Notifications: {len(notifications)}")


def main():
    parser = argparse.ArgumentParser(description="Seed demo database")
    parser.add_argument("--wipe", action="store_true", help="Truncate all data before seeding")
    parser.add_argument("--assets-dir", type=Path, default=Path(__file__).parent / "demo_assets")
    parser.add_argument("--database-url", type=str, default=os.environ.get("DATABASE_URL", ""))
    args = parser.parse_args()

    db_url = args.database_url
    if not db_url:
        print("ERROR: DATABASE_URL not set. Pass --database-url or set env var.")
        sys.exit(1)

    engine = create_engine(db_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)

    if args.wipe:
        wipe_database(engine)

    print("\nSeeding demo data...")
    db = SessionLocal()
    try:
        org = seed_org(db)
        depts = seed_departments(db, org)
        users = seed_users(db, org, depts)
        cats = seed_categories(db, org)
        vendors = seed_vendors(db, org)
        policy = seed_policies(db, org, cats, args.assets_dir, users["shreesh.exe22@gmail.com"].id)
        seed_workflows(db, org)
        seed_reports(db, users, cats, vendors, policy, args.assets_dir)
        seed_notifications(db, users)
        print("\nDone! Demo data seeded successfully.")
    except Exception as e:
        db.rollback()
        print(f"\nERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
