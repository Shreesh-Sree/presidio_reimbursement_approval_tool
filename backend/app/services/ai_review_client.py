"""Narrow HTTP boundary to the separately deployed advisory AI reviewer.

This module never imports the AI service's package, ORM, or datastore.  It
only emits a minimized, versioned event and keeps an opaque job identifier on
the report so approvers can retrieve an advisory result later.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.approval_history import ApprovalHistory
from app.models.attachment import Attachment
from app.models.expense_category import ExpenseCategory
from app.models.expense_item import ExpenseItem
from app.models.expense_report import ExpenseReport
from app.models.policy import Policy, PolicyRule
from app.models.user import User
from app.models.vendor import Vendor
from app.services import storage_service


class AIReviewError(RuntimeError):
    """The optional advisory service could not be reached or returned invalid data."""


def _reference_hmac_key() -> bytes:
    """Return the local secret used to create stable AI-service aliases.

    A dedicated key lets aliases survive AI bearer-token rotation. The bearer
    token is retained as a compatible fallback for already-configured optional
    integrations, while still keeping every exported core identifier keyed.
    """

    key = os.getenv("AI_REVIEW_REFERENCE_HMAC_KEY", "").strip()
    if not key:
        key = os.getenv("AI_REVIEW_SERVICE_TOKEN", "").strip()
    if not key:
        raise AIReviewError("AI review reference key is not configured")
    return key.encode("utf-8")


def _reference_digest(namespace: str, *values: object) -> bytes:
    material = "\x1f".join(
        (
            value.hex
            if isinstance(value, uuid.UUID)
            else value.isoformat()
            if isinstance(value, datetime)
            else str(value)
        )
        for value in values
    )
    return hmac.new(
        _reference_hmac_key(),
        f"presidio:expense-review:v1:{namespace}:{material}".encode("utf-8"),
        hashlib.sha256,
    ).digest()


def _opaque_ref(namespace: str, *values: object) -> str:
    """Return a stable HMAC alias; no core UUID leaves this boundary."""

    return f"{namespace}-{_reference_digest(namespace, *values).hex()}"


def _opaque_uuid(namespace: str, *values: object) -> uuid.UUID:
    """Preserve the service's UUID-shaped contract without exporting a core UUID."""

    return uuid.UUID(bytes=_reference_digest(namespace, *values)[:16], version=4)


def _service_url() -> str | None:
    value = os.getenv("AI_REVIEW_SERVICE_URL", "").strip().rstrip("/")
    return value or None


def _timeout() -> float:
    try:
        return max(0.1, float(os.getenv("AI_REVIEW_TIMEOUT_SECONDS", "2")))
    except ValueError:
        return 2.0


def _request(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    base_url = _service_url()
    if not base_url:
        raise AIReviewError("AI review service is not configured")
    headers = {"Accept": "application/json"}
    token = os.getenv("AI_REVIEW_SERVICE_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if payload is not None:
        data = json.dumps(payload, default=str, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(f"{base_url}{path}", data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=_timeout()) as response:  # nosec B310: URL is deployment configuration
            decoded = response.read().decode("utf-8")
    except HTTPError as exc:
        raise AIReviewError(f"AI review service returned HTTP {exc.code}") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise AIReviewError("AI review service is unavailable") from exc
    try:
        body = json.loads(decoded)
    except json.JSONDecodeError as exc:
        raise AIReviewError("AI review service returned invalid JSON") from exc
    if not isinstance(body, dict):
        raise AIReviewError("AI review service returned an invalid payload")
    return body


def _code(value: str | None, fallback: str) -> str:
    candidate = (value or fallback).upper().replace(" ", "_")
    return "".join(char for char in candidate if char.isalnum() or char in "_.:-")[:127] or fallback


def _receipt_snapshot(db: Session, item: ExpenseItem) -> dict[str, Any]:
    receipt = storage_service.latest_entity_attachment(
        db,
        entity_type="expense_item_receipt",
        entity_id=item.id,
    )
    if receipt is None:
        return {"attached": False}
    return {"attached": True, "digest": f"sha256:{receipt.checksum}"}


def _policy_rules_snapshot(db: Session, policy: Policy, items: list[ExpenseItem]) -> list[dict[str, Any]]:
    category_ids = {item.category_id for item in items}
    categories = {
        category.id: category
        for category in db.query(ExpenseCategory).filter(ExpenseCategory.id.in_(category_ids)).all()
    } if category_ids else {}
    vendor_ids = {rule.vendor_id for rule in policy.rules if rule.vendor_id is not None}
    vendors = {
        vendor.id: vendor
        for vendor in db.query(Vendor).filter(Vendor.id.in_(vendor_ids)).all()
    } if vendor_ids else {}

    snapshots: list[dict[str, Any]] = []
    for rule in policy.rules:
        if rule.is_deleted:
            continue
        category = categories.get(rule.category_id) if rule.category_id else None
        # A global rule is represented once per submitted category, so the AI
        # contract always has a concrete classification code.
        scoped_categories = [category] if category else list(categories.values())
        for scoped in scoped_categories:
            if scoped is None:
                continue
            allowed_vendor_codes: list[str] = []
            if rule.vendor_id and rule.vendor_id in vendors:
                allowed_vendor_codes.append(_code(vendors[rule.vendor_id].normalized_name, "VENDOR"))
            snapshots.append(
                {
                    "rule_ref": _opaque_ref("rule", rule.id),
                    "category_code": _code(scoped.code, "UNCATEGORIZED"),
                    "max_per_item": str(scoped.max_amount) if scoped.max_amount is not None else None,
                    "max_per_report": str(rule.max_per_trip) if rule.max_per_trip is not None else None,
                    "receipt_required_at_or_above": (
                        str(rule.receipt_required_above) if rule.receipt_required_above is not None else None
                    ),
                    "allowed_vendor_codes": allowed_vendor_codes,
                    "vendor_caps": {},
                }
            )
    if snapshots:
        return snapshots

    # Policies without structured rules are valid for the core app, but the AI
    # contract requires at least one rule.  Send category-only default rules;
    # the reviewer can then flag them as unconfigured instead of failing.
    return [
        {
            "rule_ref": _opaque_ref("rule", policy.id, category.id, "default"),
            "category_code": _code(category.code, "UNCATEGORIZED"),
            "allowed_vendor_codes": [],
            "vendor_caps": {},
        }
        for category in categories.values()
    ]


def _historical_baselines(
    db: Session,
    report: ExpenseReport,
    category_ids: set[uuid.UUID],
    categories: dict[uuid.UUID, ExpenseCategory],
) -> list[dict[str, Any]]:
    """Return department-scoped, aggregate-only category history.

    The AI service receives neither report identifiers nor employee history.
    Each historical observation is a report-level category total, never an
    individual line item. That prevents a multi-line report from overweighting
    an employee's history. Cohorts with fewer than three reports are removed
    in the query, before anything crosses the service boundary.
    """

    if not category_ids:
        return []
    report_category_totals = (
        db.query(
            ExpenseItem.expense_report_id.label("report_id"),
            ExpenseItem.category_id,
            func.sum(ExpenseItem.amount).label("report_category_total"),
        )
        .join(ExpenseReport, ExpenseReport.id == ExpenseItem.expense_report_id)
        .filter(
            ExpenseReport.department_id == report.department_id,
            ExpenseReport.id != report.id,
            ExpenseReport.status.in_(("approved_pending_payment", "paid")),
            ExpenseReport.is_deleted.is_(False),
            ExpenseItem.category_id.in_(category_ids),
            ExpenseItem.currency_code == report.currency_code,
            ExpenseItem.is_deleted.is_(False),
        )
        .group_by(ExpenseItem.expense_report_id, ExpenseItem.category_id)
        .subquery()
    )
    rows = (
        db.query(
            report_category_totals.c.category_id,
            func.avg(report_category_totals.c.report_category_total).label("average_amount"),
            func.count(report_category_totals.c.report_id).label("sample_size"),
        )
        .group_by(report_category_totals.c.category_id)
        .having(func.count(report_category_totals.c.report_id) >= 3)
        .all()
    )
    baselines: list[dict[str, Any]] = []
    for category_id, average_amount, sample_size in rows:
        category = categories.get(category_id)
        if category is None or average_amount is None:
            continue
        baselines.append(
            {
                "category_code": _code(category.code, "UNCATEGORIZED"),
                "average_amount": str(Decimal(average_amount).quantize(Decimal("0.01"))),
                "sample_size": int(sample_size),
            }
        )
    return baselines


def _known_receipt_digests(
    db: Session,
    report: ExpenseReport,
) -> list[str]:
    """Return prior department receipt hashes without exposing claim details."""

    rows = (
        db.query(Attachment.checksum)
        .join(ExpenseItem, Attachment.entity_id == ExpenseItem.id)
        .join(ExpenseReport, ExpenseReport.id == ExpenseItem.expense_report_id)
        .filter(
            Attachment.entity_type == "expense_item_receipt",
            Attachment.is_deleted.is_(False),
            ExpenseReport.department_id == report.department_id,
            ExpenseReport.id != report.id,
            ExpenseReport.status.in_(("submitted", "approved_pending_payment", "paid")),
            ExpenseReport.is_deleted.is_(False),
            ExpenseItem.is_deleted.is_(False),
        )
        .all()
    )
    return sorted({f"sha256:{str(checksum).lower()}" for (checksum,) in rows if checksum})


def build_review_event(db: Session, report: ExpenseReport) -> dict[str, Any] | None:
    """Build a PII-minimized event from a frozen submitted report snapshot."""

    if not report.applied_policy_id:
        return None
    employee = db.get(User, report.employee_user_id)
    if employee is None or employee.is_deleted:
        return None
    policy = (
        db.query(Policy)
        .filter(
            Policy.id == report.applied_policy_id,
            Policy.organization_id == employee.organization_id,
            Policy.is_deleted.is_(False),
        )
        .first()
    )
    if policy is None:
        return None
    items = (
        db.query(ExpenseItem)
        .filter(ExpenseItem.expense_report_id == report.id, ExpenseItem.is_deleted.is_(False))
        .order_by(ExpenseItem.line_number)
        .all()
    )
    if not items:
        return None
    category_ids = {item.category_id for item in items}
    categories = {
        category.id: category
        for category in db.query(ExpenseCategory).filter(ExpenseCategory.id.in_(category_ids)).all()
    }
    vendor_ids = {item.vendor_id for item in items if item.vendor_id is not None}
    vendors = {
        vendor.id: vendor
        for vendor in db.query(Vendor).filter(Vendor.id.in_(vendor_ids)).all()
    } if vendor_ids else {}
    event_id = _opaque_uuid("event", report.id, report.applied_policy_id, report.submitted_at)
    prior_submissions = (
        db.query(ApprovalHistory.id)
        .filter(
            ApprovalHistory.expense_report_id == report.id,
            ApprovalHistory.action.in_(("submitted", "resubmitted")),
        )
        .count()
    )
    return {
        "event_id": str(event_id),
        "event_type": "expense_report.resubmitted" if prior_submissions > 1 else "expense_report.submitted",
        "event_version": "1.0",
        "occurred_at": (report.submitted_at or datetime.now(UTC)).isoformat(),
        "report_id": str(_opaque_uuid("report", report.id)),
        "tenant_ref": _opaque_ref("tenant", employee.organization_id),
        "submitter_ref": _opaque_ref("subject", report.employee_user_id),
        "items": [
            {
                "line_id": str(_opaque_uuid("line", item.id)),
                "expense_date": item.expense_date.isoformat(),
                "category_code": _code(categories.get(item.category_id).code if item.category_id in categories else None, "UNCATEGORIZED"),
                "vendor_code": _code(vendors[item.vendor_id].normalized_name, "VENDOR") if item.vendor_id in vendors else None,
                "amount": str(Decimal(item.amount)),
                "currency": (item.currency_code or report.currency_code).upper(),
                "receipt": _receipt_snapshot(db, item),
            }
            for item in items
        ],
        "policy": {
            "policy_version_ref": _opaque_ref("policy", policy.id),
            "rules": _policy_rules_snapshot(db, policy, items),
        },
        "historical_baselines": _historical_baselines(db, report, category_ids, categories),
        "known_receipt_digests": _known_receipt_digests(db, report),
    }


def request_review(db: Session, report: ExpenseReport) -> str | None:
    """Enqueue an advisory review and retain only its opaque job identifier."""

    if _service_url() is None:
        return None
    event = build_review_event(db, report)
    if event is None:
        return None
    job = _request("POST", "/v1/review-jobs", event)
    try:
        job_id = uuid.UUID(str(job["id"]))
    except (KeyError, ValueError, TypeError) as exc:
        raise AIReviewError("AI review service returned a job without a valid ID") from exc
    if os.getenv("AI_REVIEW_PROCESS_INLINE", "").lower() in {"1", "true", "yes"}:
        job = _request("POST", f"/v1/review-jobs/{job_id}/process")
    report.ai_review_job_id = job_id
    report.ai_review_requested_at = datetime.now(UTC)
    db.commit()
    return str(job_id)


def review_payload(report: ExpenseReport) -> dict[str, Any] | None:
    """Return a compact advisory payload for an approver UI; failures stay advisory."""

    if report.ai_review_job_id is None:
        return None
    try:
        job = _request("GET", f"/v1/review-jobs/{report.ai_review_job_id}")
    except AIReviewError:
        return {
            "status": "unavailable",
            "job_id": str(report.ai_review_job_id),
            "human_review": {"required": True, "automated_action_taken": False},
        }
    result = job.get("result") or {}
    return {
        "status": job.get("status"),
        "job_id": str(report.ai_review_job_id),
        "summary": result.get("summary"),
        "key_insights": result.get("key_insights", []),
        "recommendation": result.get("recommendation"),
        "cited_finding_ids": result.get("cited_finding_ids", []),
        "cited_policy_rule_refs": result.get("cited_policy_rule_refs", []),
        "findings": (result.get("evaluation") or {}).get("findings", []),
        "risk_level": (result.get("evaluation") or {}).get("risk_level"),
        "provider": result.get("provider"),
        "human_review": result.get("human_review") or {"required": True, "automated_action_taken": False},
    }


def record_human_disposition(report: ExpenseReport, reviewer_id: uuid.UUID | str, action: str, remarks: str | None) -> None:
    """Best-effort advisory disposition; it never changes core workflow state."""

    if report.ai_review_job_id is None or _service_url() is None:
        return
    try:
        job = _request("GET", f"/v1/review-jobs/{report.ai_review_job_id}")
        if job.get("status") != "completed":
            return
        _request(
            "POST",
            f"/v1/review-jobs/{report.ai_review_job_id}/dispositions",
            {
                "reviewer_ref": _opaque_ref("subject", reviewer_id),
                "action": action,
                "remarks": remarks,
                "finding_ids": [],
            },
        )
    except AIReviewError:
        # A review disposition is an AI-service audit enhancement, not a
        # workflow prerequisite.  The core approval audit remains authoritative.
        return
