"""Privacy-safe historical signals supplied to the isolated AI reviewer."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.models.attachment import Attachment
from app.models.expense_item import ExpenseItem
from app.services import ai_review_client
from app.services.report_service import create_draft

from .test_ai_review_boundary import _submitted_snapshot


def _historical_report(
    db,
    seeded_user,
    seeded_category,
    *,
    amount: Decimal | None = None,
    amounts: tuple[Decimal, ...] | None = None,
    checksum: str,
) -> None:
    line_amounts = amounts or ((amount,) if amount is not None else ())
    assert line_amounts
    report = create_draft(db, seeded_user.id, seeded_user.department_id, "Prior approved travel")
    report.status = "approved_pending_payment"
    for line_number, line_amount in enumerate(line_amounts, start=1):
        item = ExpenseItem(
            expense_report_id=report.id,
            line_number=line_number,
            category_id=seeded_category.id,
            amount=line_amount,
            original_amount=line_amount,
            currency_code="USD",
            expense_date=date.today(),
        )
        db.add(item)
        db.flush()
        db.add(
            Attachment(
                entity_type="expense_item_receipt",
                entity_id=item.id,
                file_name="prior.pdf",
                original_file_name="prior.pdf",
                storage_path="local://test/prior.pdf",
                mime_type="application/pdf",
                file_size_bytes=10,
                checksum=checksum,
                uploaded_by=seeded_user.id,
            )
        )
    db.commit()


def test_ai_event_includes_only_aggregate_history_and_receipt_hashes(
    db, seeded_user, seeded_policy, seeded_category
):
    report = _submitted_snapshot(db, seeded_user, seeded_policy, seeded_category)
    current_attachment = db.query(Attachment).filter(Attachment.entity_type == "expense_item_receipt").one()
    current_attachment.checksum = "b" * 64
    db.commit()

    for _ in range(3):
        _historical_report(
            db,
            seeded_user,
            seeded_category,
            amount=Decimal("50.00"),
            checksum="b" * 64,
        )

    event = ai_review_client.build_review_event(db, report)

    assert event is not None
    assert event["known_receipt_digests"] == [f"sha256:{'b' * 64}"]
    assert event["historical_baselines"] == [
        {"category_code": "TRAVEL", "average_amount": "50.00", "sample_size": 3}
    ]
    serialized = str(event)
    assert "Prior approved travel" not in serialized
    assert "employee@example.com" not in serialized


def test_ai_history_averages_category_totals_per_report(db, seeded_user, seeded_policy, seeded_category):
    report = _submitted_snapshot(db, seeded_user, seeded_policy, seeded_category)
    _historical_report(
        db,
        seeded_user,
        seeded_category,
        amounts=(Decimal("50.00"), Decimal("100.00")),
        checksum="c" * 64,
    )
    _historical_report(
        db,
        seeded_user,
        seeded_category,
        amount=Decimal("50.00"),
        checksum="d" * 64,
    )
    _historical_report(
        db,
        seeded_user,
        seeded_category,
        amount=Decimal("100.00"),
        checksum="e" * 64,
    )

    event = ai_review_client.build_review_event(db, report)

    assert event is not None
    assert event["historical_baselines"] == [
        {"category_code": "TRAVEL", "average_amount": "100.00", "sample_size": 3}
    ]


def test_ai_history_omits_category_cohorts_smaller_than_three_reports(
    db, seeded_user, seeded_policy, seeded_category
):
    report = _submitted_snapshot(db, seeded_user, seeded_policy, seeded_category)
    for amount in (Decimal("50.00"), Decimal("100.00")):
        _historical_report(
            db,
            seeded_user,
            seeded_category,
            amount=amount,
            checksum="f" * 64,
        )

    event = ai_review_client.build_review_event(db, report)

    assert event is not None
    assert event["historical_baselines"] == []
