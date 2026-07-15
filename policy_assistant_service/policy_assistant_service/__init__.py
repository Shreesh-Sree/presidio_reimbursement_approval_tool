"""Standalone policy-grounded retrieval assistant.

The package intentionally has no dependency on the reimbursement application's
ORM, database configuration, or workflow services.
"""

from .api import create_app

__all__ = ["create_app"]
