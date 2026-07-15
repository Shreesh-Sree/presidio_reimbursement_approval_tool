from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from ai_review_service.contracts import (
    ExpenseLineSnapshot,
    ExpenseReviewRequested,
    HistoricalCategoryBaseline,
    PolicyRuleSnapshot,
    PolicySnapshot,
    ReceiptEvidence,
)


def make_event(
    *,
    event_id: UUID | None = None,
    report_id: UUID | None = None,
    items: tuple[ExpenseLineSnapshot, ...] | None = None,
    known_receipt_digests: tuple[str, ...] = (),
    baselines: tuple[HistoricalCategoryBaseline, ...] = (),
) -> ExpenseReviewRequested:
    return ExpenseReviewRequested(
        event_id=event_id or uuid4(),
        report_id=report_id or uuid4(),
        tenant_ref="tenant:demo",
        submitter_ref="subject:7f92a",
        items=items
        or (
            ExpenseLineSnapshot(
                line_id=uuid4(),
                expense_date=date(2026, 7, 1),
                category_code="travel",
                subcategory_code="airfare",
                vendor_code="airline_a",
                amount=Decimal("80.00"),
                currency="usd",
                description_excerpt="Client travel",
                receipt=ReceiptEvidence(attached=True, digest="a" * 64),
            ),
        ),
        policy=PolicySnapshot(
            policy_version_ref="travel-v2",
            rules=(
                PolicyRuleSnapshot(
                    rule_ref="travel-airfare-v2",
                    category_code="travel",
                    subcategory_code="airfare",
                    max_per_item=Decimal("100.00"),
                    max_per_report=Decimal("150.00"),
                    receipt_required_at_or_above=Decimal("50.00"),
                    allowed_vendor_codes=("airline_a",),
                    vendor_caps={"airline_a": Decimal("90.00")},
                ),
            ),
        ),
        historical_baselines=baselines,
        known_receipt_digests=known_receipt_digests,
    )


@pytest.fixture
def event_factory():
    return make_event
