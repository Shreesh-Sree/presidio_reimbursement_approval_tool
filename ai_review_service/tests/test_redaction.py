import pytest
from pydantic import ValidationError

from ai_review_service.contracts import ExpenseReviewRequested, ReceiptEvidence
from ai_review_service.redaction import minimise_event, provider_context, provider_prompt, pseudonymize
from ai_review_service.rules import RuleEvaluator


def test_event_is_redacted_before_persistence_or_provider_use(event_factory):
    event = event_factory(
        items=(
            event_factory().items[0].model_copy(
                update={
                    "description_excerpt": "Contact jane.doe@example.com or +1 (415) 555-0134 at https://example.test/receipt",
                    "receipt": event_factory().items[0].receipt.model_copy(update={"digest": "f" * 64}),
                }
            ),
        )
    )

    minimized = minimise_event(event)
    description = minimized.items[0].description_excerpt or ""
    assert "jane.doe@example.com" not in description
    assert "415" not in description
    assert "https://" not in description
    assert "[email redacted]" in description

    context = provider_context(RuleEvaluator().evaluate(minimized), item_count=len(minimized.items))
    prompt = provider_prompt(context)
    assert str(event.report_id) not in prompt
    assert event.submitter_ref not in prompt
    assert "f" * 64 not in prompt
    assert "jane.doe@example.com" not in prompt


def test_pseudonymization_is_stable_and_not_reversible_by_inspection():
    reference = pseudonymize("jane.doe@example.com", secret="test-secret")

    assert reference == pseudonymize("jane.doe@example.com", secret="test-secret")
    assert reference.startswith("anon:")
    assert "jane" not in reference


def test_contract_rejects_direct_reference_and_receipt_url(event_factory):
    event = event_factory()
    payload = event.model_dump(mode="python")
    payload["submitter_ref"] = "jane.doe@example.com"
    with pytest.raises(ValidationError):
        ExpenseReviewRequested.model_validate(payload)

    with pytest.raises(ValidationError):
        ReceiptEvidence(attached=True, digest="https://storage.example.test/receipt.pdf")
