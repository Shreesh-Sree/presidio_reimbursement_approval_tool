"""Isolated, advisory-only expense review service.

The package deliberately has no imports from the reimbursement application's
ORM, routes, or database.  Its only input is a versioned event contract.
"""

from .api import create_app
from .service import ExpenseReviewService

__all__ = ["ExpenseReviewService", "create_app"]
