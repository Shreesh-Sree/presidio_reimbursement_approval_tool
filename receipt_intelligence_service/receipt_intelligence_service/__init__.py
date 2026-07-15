"""Isolated, deterministic receipt metadata analysis service.

The package intentionally has no imports from the reimbursement API, ORM, or
database models. Its API accepts an event-shaped metadata contract only.
"""

from .api import create_app
from .service import ReceiptIntelligenceService

__all__ = ["ReceiptIntelligenceService", "create_app"]
