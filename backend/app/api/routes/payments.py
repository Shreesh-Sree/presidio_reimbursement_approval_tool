"""Finance queue, export batches, and guarded reimbursement payment actions."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.payment_schemas import PaymentBatchCreateInput, PaymentFailedInput, PaymentPaidInput
from app.core.database import get_db
from app.core.deps import require_permission
from app.services import notification_delivery_service, payment_service


router = APIRouter(prefix="/api/payments", tags=["payments"])


def _raise_payment_error(exc: Exception) -> None:
    if isinstance(exc, payment_service.PaymentNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(
        exc,
        (payment_service.PaymentTransitionError, payment_service.PaymentValidationError),
    ):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    raise exc


def _scope(user: dict[str, object]) -> tuple[str, str]:
    return str(user["organization_id"]), str(user["user_id"])


@router.get("")
async def finance_queue(
    status_filter: str | None = Query(default=None, alias="status"),
    batch_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("payment:manage")),
):
    organization_id, _actor_id = _scope(user)
    try:
        payments, total = payment_service.list_payments(
            db,
            organization_id,
            status=status_filter,
            batch_id=batch_id,
            limit=limit,
            offset=offset,
        )
        return {
            "items": [
                payment_service.payment_payload(db, payment, include_finance_details=True)
                for payment in payments
            ],
            "total": total,
        }
    except Exception as exc:
        _raise_payment_error(exc)


@router.get("/batches")
async def list_payment_batches(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("payment:manage")),
):
    organization_id, _actor_id = _scope(user)
    try:
        batches, total = payment_service.list_batches(db, organization_id, limit=limit, offset=offset)
        return {"items": [payment_service.batch_payload(db, batch) for batch in batches], "total": total}
    except Exception as exc:
        _raise_payment_error(exc)


@router.post("/batches", status_code=status.HTTP_201_CREATED)
async def create_payment_batch(
    payload: PaymentBatchCreateInput,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("payment:manage")),
):
    organization_id, actor_id = _scope(user)
    try:
        batch = payment_service.create_batch(
            db,
            organization_id,
            actor_id,
            payload.payment_ids,
            remarks=payload.remarks,
        )
        return payment_service.batch_payload(db, batch, include_payments=True)
    except Exception as exc:
        _raise_payment_error(exc)


@router.get("/batches/{batch_id}")
async def get_payment_batch(
    batch_id: str,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("payment:manage")),
):
    organization_id, _actor_id = _scope(user)
    try:
        batch = payment_service.get_batch(db, batch_id, organization_id)
        return payment_service.batch_payload(db, batch, include_payments=True)
    except Exception as exc:
        _raise_payment_error(exc)


@router.post("/batches/{batch_id}/export")
async def export_payment_batch(
    batch_id: str,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("payment:manage")),
):
    organization_id, actor_id = _scope(user)
    try:
        batch, csv_content = payment_service.export_batch(db, batch_id, organization_id, actor_id)
        return Response(
            content=csv_content,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{batch.batch_reference}.csv"'},
        )
    except Exception as exc:
        _raise_payment_error(exc)


@router.get("/{payment_id}")
async def get_payment(
    payment_id: str,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("payment:manage")),
):
    organization_id, _actor_id = _scope(user)
    try:
        payment = payment_service.get_payment(db, payment_id, organization_id)
        return payment_service.payment_payload(
            db,
            payment,
            include_history=True,
            include_finance_details=True,
        )
    except Exception as exc:
        _raise_payment_error(exc)


@router.post("/{payment_id}/mark-paid")
async def mark_payment_paid(
    payment_id: str,
    payload: PaymentPaidInput,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("payment:manage")),
):
    organization_id, actor_id = _scope(user)
    try:
        payment = payment_service.mark_paid(
            db,
            payment_id,
            organization_id,
            actor_id,
            provider_reference=payload.provider_reference,
            payment_date=payload.payment_date,
            remarks=payload.remarks,
        )
        notification_delivery_service.enqueue_pending_email_delivery(background_tasks)
        return payment_service.payment_payload(
            db,
            payment,
            include_history=True,
            include_finance_details=True,
        )
    except Exception as exc:
        _raise_payment_error(exc)


@router.post("/{payment_id}/mark-failed")
async def mark_payment_failed(
    payment_id: str,
    payload: PaymentFailedInput,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("payment:manage")),
):
    organization_id, actor_id = _scope(user)
    try:
        payment = payment_service.mark_failed(
            db,
            payment_id,
            organization_id,
            actor_id,
            failure_reason=payload.failure_reason,
            remarks=payload.remarks,
        )
        notification_delivery_service.enqueue_pending_email_delivery(background_tasks)
        return payment_service.payment_payload(
            db,
            payment,
            include_history=True,
            include_finance_details=True,
        )
    except Exception as exc:
        _raise_payment_error(exc)
