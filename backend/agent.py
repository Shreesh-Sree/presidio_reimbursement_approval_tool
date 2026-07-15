"""Retired in-process AI module.

Expense analysis now lives in the separately deployable ``ai_review_service``.
Keeping this import-safe stub prevents a legacy import from accidentally
reintroducing direct access to reimbursement records, raw receipts, or model
provider credentials.
"""


class LegacyAIIntegrationError(RuntimeError):
    pass


def analyze_expense_report(*_args, **_kwargs):
    raise LegacyAIIntegrationError(
        "In-process AI review was retired. Configure AI_REVIEW_SERVICE_URL and use ai_review_service instead."
    )
