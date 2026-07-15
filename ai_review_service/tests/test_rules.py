from datetime import date
from decimal import Decimal
from uuid import uuid4

from ai_review_service.contracts import (
    ExpenseLineSnapshot,
    FindingSeverity,
    FindingType,
    HistoricalCategoryBaseline,
    ReceiptEvidence,
)
from ai_review_service.rules import RuleEvaluator


def test_rule_evaluator_flags_caps_receipts_duplicates_and_anomalies(event_factory):
    repeated_digest = "b" * 64
    items = (
        ExpenseLineSnapshot(
            line_id=uuid4(),
            expense_date=date(2026, 7, 1),
            category_code="travel",
            subcategory_code="airfare",
            vendor_code="airline_a",
            amount=Decimal("120.00"),
            currency="usd",
            receipt=ReceiptEvidence(attached=False),
        ),
        ExpenseLineSnapshot(
            line_id=uuid4(),
            expense_date=date(2026, 7, 2),
            category_code="travel",
            subcategory_code="airfare",
            vendor_code="airline_a",
            amount=Decimal("40.00"),
            currency="usd",
            receipt=ReceiptEvidence(attached=True, digest=repeated_digest),
        ),
    )
    event = event_factory(
        items=items,
        known_receipt_digests=(repeated_digest,),
        baselines=(
            HistoricalCategoryBaseline(
                category_code="travel",
                average_amount=Decimal("50.00"),
                sample_size=5,
                alert_multiplier=Decimal("2.00"),
            ),
        ),
    )

    evaluation = RuleEvaluator().evaluate(event)

    finding_types = {finding.finding_type for finding in evaluation.findings}
    assert FindingType.POLICY_LIMIT_EXCEEDED in finding_types
    assert FindingType.VENDOR_CAP_EXCEEDED in finding_types
    assert FindingType.MISSING_RECEIPT in finding_types
    assert FindingType.POLICY_REPORT_CAP_EXCEEDED in finding_types
    assert FindingType.POTENTIAL_DUPLICATE in finding_types
    assert FindingType.UNUSUAL_SPEND in finding_types
    assert evaluation.report_total == Decimal("160.00")
    assert evaluation.risk_level == FindingSeverity.HIGH


def test_rule_evaluator_marks_unconfigured_category(event_factory):
    event = event_factory(
        items=(
            ExpenseLineSnapshot(
                line_id=uuid4(),
                expense_date=date(2026, 7, 1),
                category_code="office",
                amount=Decimal("25.00"),
                currency="USD",
                receipt=ReceiptEvidence(attached=True),
            ),
        )
    )

    evaluation = RuleEvaluator().evaluate(event)

    assert [finding.finding_type for finding in evaluation.findings] == [
        FindingType.UNCONFIGURED_CATEGORY
    ]
