"""Durable-work runner intended for a scheduler/worker process.

Run ``python -m app.worker --once`` from a platform scheduler at a bounded
cadence.  It intentionally performs no browser-request work and is safe to
run concurrently because notification/outbox claims use leases.
"""

from __future__ import annotations

import argparse

from app.core.database import get_session_local
from app.services import approval_service, integration_outbox_service, notification_delivery_service


def run_once() -> dict[str, int]:
    session = get_session_local()()
    try:
        escalated = approval_service.process_overdue_approvals(session)
        email_deliveries = notification_delivery_service.deliver_pending_email_notifications(session)
        ai_deliveries = integration_outbox_service.deliver_pending_ai_reviews(session)
        return {
            "overdue_escalations": escalated,
            "email_deliveries": email_deliveries,
            "ai_review_deliveries": ai_deliveries,
        }
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Process Presidio durable background work once")
    parser.add_argument("--once", action="store_true", help="required safety switch; do not run an in-process loop")
    args = parser.parse_args()
    if not args.once:
        parser.error("--once is required; scheduling is owned by the deployment platform")
    print(run_once())  # noqa: T201 - intentionally provides a scheduler-readable result


if __name__ == "__main__":  # pragma: no cover - exercised by deployment scheduler
    main()
