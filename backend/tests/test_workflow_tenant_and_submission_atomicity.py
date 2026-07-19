"""Tenant scope and failure-path coverage for approval submission."""

from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal

import pytest
from fastapi import BackgroundTasks

from app.api.routes import reports
from app.models.expense_item import ExpenseItem
from app.models.expense_report import ExpenseReport
from app.models.organization import Organization
from app.models.workflow_rule import WorkflowRule
from app.services import approval_service
from app.services.report_service import create_draft


def test_same_workflow_name_is_valid_per_tenant_and_lookup_never_crosses(db, seeded_user):
    other_org = Organization(name="Workflow Other", code="WORKFLOW-OTHER")
    db.add(other_org)
    db.flush()
    own_rule = WorkflowRule(
        organization_id=seeded_user.organization_id,
        name="Default approvals",
        conditions_json={},
        approval_chain_json=[],
    )
    foreign_rule = WorkflowRule(
        organization_id=other_org.id,
        name="Default approvals",
        conditions_json={},
        approval_chain_json=[],
    )
    report = ExpenseReport(
        report_number="RPT-TENANT-WORKFLOW",
        employee_user_id=seeded_user.id,
        department_id=seeded_user.department_id,
        title="Tenant scoped workflow",
        currency_code="USD",
        status="submitted",
        total_amount=Decimal("10.00"),
    )
    db.add_all((own_rule, foreign_rule, report))
    db.commit()

    assert approval_service._matching_rule(db, report, seeded_user.organization_id).id == own_rule.id
    assert approval_service._matching_rule(db, report, other_org.id).id == foreign_rule.id


def test_submit_rolls_back_status_when_workflow_initialization_fails(
    db, seeded_user, seeded_policy, seeded_category, monkeypatch
):
    report = create_draft(db, seeded_user.id, seeded_user.department_id, "Atomic submit")
    db.add(
        ExpenseItem(
            expense_report_id=report.id,
            line_number=1,
            category_id=seeded_category.id,
            amount=Decimal("25.00"),
            original_amount=Decimal("25.00"),
            currency_code="USD",
            expense_date=date.today(),
        )
    )
    db.commit()

    monkeypatch.setattr(approval_service, "validate_workflow_for_report", lambda *_args, **_kwargs: None)

    def fail_workflow(*_args, **_kwargs):
        raise approval_service.ApprovalError("Injected workflow failure")

    monkeypatch.setattr(approval_service, "init_workflow", fail_workflow)
    actor = {
        "user_id": str(seeded_user.id),
        "organization_id": str(seeded_user.organization_id),
        "department_id": str(seeded_user.department_id),
        "permissions": ["report:create"],
    }
    with pytest.raises(Exception):
        asyncio.run(reports.submit_report(str(report.id), BackgroundTasks(), db, actor))

    db.expire_all()
    restored = db.get(ExpenseReport, report.id)
    assert restored is not None
    assert restored.status == "draft"
    assert restored.submitted_at is None
