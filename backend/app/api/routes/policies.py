"""Policy version and policy-document API routes."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_permission
from app.services import policy_assistant_client, policy_document_text, policy_service, policy_template_service, storage_service
from app.services.upload_guard import UploadTooLargeError, read_bounded_upload_sync


router = APIRouter(prefix="/api/policies", tags=["policies"])


@router.get("/templates/excel")
def download_excel_template():
    content = policy_template_service.generate_excel_template()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="policy_rules_template.xlsx"'},
    )


@router.get("/templates/pdf")
def download_pdf_template():
    content = policy_template_service.generate_pdf_template()
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="policy_rules_template.pdf"'},
    )


@router.post("/extract")
def extract_and_apply_policy(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: dict[str, str] = Depends(require_permission("policy:manage")),
):
    filename = file.filename or "policy_upload"
    try:
        file_bytes = read_bounded_upload_sync(file, max_bytes=10 * 1024 * 1024)
    except UploadTooLargeError as exc:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)) from exc

    if filename.lower().endswith(".xlsx") or filename.lower().endswith(".csv"):
        extracted_rules = policy_template_service.extract_rules_from_excel(file_bytes)
    elif filename.lower().endswith(".pdf"):
        extracted_rules = policy_template_service.extract_rules_from_pdf(file_bytes)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload an Excel (.xlsx, .csv) or PDF (.pdf) file.",
        )

    if not extracted_rules:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not extract any valid policy rules from the uploaded document.",
        )

    result = policy_template_service.apply_extracted_rules(db, user["organization_id"], extracted_rules)
    return result



class PolicyRuleInput(BaseModel):
    category_id: str | None = None
    category_name: str | None = None
    vendor_id: str | None = None
    vendor_name: str | None = None
    max_per_day: Decimal | None = Field(default=None, ge=0)
    max_per_trip: Decimal | None = Field(default=None, ge=0)
    per_category_cap: Decimal | None = Field(default=None, ge=0)
    receipt_required_above: Decimal | None = Field(default=None, ge=0)


class PolicyCreateInput(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    version_label: str = Field(min_length=1, max_length=50)
    effective_from: datetime | date
    effective_to: datetime | date | None = None
    rules: list[PolicyRuleInput] = Field(default_factory=list)


class PolicyUpdateInput(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    version_label: str | None = Field(default=None, min_length=1, max_length=50)
    effective_from: datetime | date | None = None
    effective_to: datetime | date | None = None
    rules: list[PolicyRuleInput] | None = None


class PolicyAssistantIndexInput(BaseModel):
    """Explicit administrator-supplied evidence for the isolated RAG assistant."""

    content: str = Field(min_length=1, max_length=50_000)


class PolicyAssistantQuestionInput(BaseModel):
    """A bounded, read-only policy question; answers are always advisory."""

    question: str = Field(min_length=1, max_length=1_200)
    top_k: int | None = Field(default=None, ge=1, le=8)


def _policy_error(exc: Exception) -> None:
    if isinstance(exc, policy_service.PolicyNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, policy_service.PolicyConflictError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if isinstance(exc, storage_service.UploadValidationError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if isinstance(exc, storage_service.StorageError):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    if isinstance(exc, policy_assistant_client.PolicyAssistantError):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    raise exc


@router.get("")
def list_policies(
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("policy:manage")),
):
    return [
        policy_service.policy_payload(db, policy)
        for policy in policy_service.list_policies(db, user["organization_id"])
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_policy(
    payload: PolicyCreateInput,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("policy:manage")),
):
    try:
        policy = policy_service.create_policy_version(
            db,
            payload.name,
            payload.version_label,
            payload.effective_from,
            organization_id=user["organization_id"],
            effective_to=payload.effective_to,
            rules_data=payload.rules,
        )
        return policy_service.policy_payload(db, policy)
    except Exception as exc:
        _policy_error(exc)


@router.get("/{policy_id}")
def get_policy(
    policy_id: str,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("policy:manage")),
):
    try:
        return policy_service.policy_payload(
            db,
            policy_service.get_policy(db, policy_id, user["organization_id"]),
        )
    except Exception as exc:
        _policy_error(exc)


@router.patch("/{policy_id}")
def update_policy(
    policy_id: str,
    payload: PolicyUpdateInput,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("policy:manage")),
):
    try:
        changes: dict[str, Any] = payload.model_dump(exclude_unset=True)
        if "rules" in changes and changes["rules"] is not None:
            changes["rules_data"] = changes.pop("rules")
        policy = policy_service.update_policy_version(
            db,
            policy_id,
            organization_id=user["organization_id"],
            **changes,
        )
        return policy_service.policy_payload(db, policy)
    except Exception as exc:
        _policy_error(exc)


@router.post("/{policy_id}/activate")
def activate_policy(
    policy_id: str,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("policy:manage")),
):
    try:
        return policy_service.policy_payload(
            db,
            policy_service.activate_policy(
                db,
                policy_id,
                organization_id=user["organization_id"],
            ),
        )
    except Exception as exc:
        _policy_error(exc)


@router.post("/{policy_id}/assistant-index")
def index_policy_for_assistant(
    policy_id: str,
    payload: PolicyAssistantIndexInput,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("policy:manage")),
):
    """Index explicit policy evidence without coupling core persistence to RAG data."""

    try:
        policy = policy_service.get_policy(db, policy_id, user["organization_id"])
        indexing = policy_assistant_client.index_policy_text(
            organization_id=str(user["organization_id"]),
            policy_id=str(policy.id),
            content=payload.content,
        )
        return {"policy_id": str(policy.id), "indexing": indexing}
    except Exception as exc:
        _policy_error(exc)


@router.post("/{policy_id}/assistant-ask")
def ask_policy_assistant(
    policy_id: str,
    payload: PolicyAssistantQuestionInput,
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("policy:manage")),
):
    """Return a cited policy answer from the isolated assistant, if configured."""

    try:
        policy = policy_service.get_policy(db, policy_id, user["organization_id"])
        answer = policy_assistant_client.ask_policy(
            organization_id=str(user["organization_id"]),
            policy_id=str(policy.id),
            question=payload.question,
            top_k=payload.top_k,
        )
        return {"policy_id": str(policy.id), "answer": answer}
    except Exception as exc:
        _policy_error(exc)


@router.post("/{policy_id}/upload-doc")
def upload_policy_document(
    policy_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: dict[str, object] = Depends(require_permission("policy:manage")),
):
    attachment = None
    stored_path: str | None = None
    committed = False
    try:
        policy = policy_service.get_policy(db, policy_id, user["organization_id"])
        content = read_bounded_upload_sync(
            file, max_bytes=storage_service._max_upload_bytes("policy_document")
        )
        attachment = storage_service.create_attachment(
            db,
            entity_type="policy_document",
            entity_id=policy.id,
            uploaded_by=user["user_id"],
            file_name=file.filename or "policy-document",
            mime_type=file.content_type or "",
            content=content,
            kind="policy_document",
        )
        stored_path = attachment.storage_path
        policy_service.attach_document(
            db,
            policy.id,
            attachment.id,
            organization_id=user["organization_id"],
        )
        db.commit()
        committed = True
        db.refresh(policy)
        response = policy_service.policy_payload(db, policy)
        try:
            extracted_text = policy_document_text.extract_policy_text(
                file_name=attachment.original_file_name,
                content=content,
            )
            indexing = policy_assistant_client.index_policy_text(
                organization_id=str(user["organization_id"]),
                policy_id=str(policy.id),
                content=extracted_text,
            )
            response["assistant_indexing"] = {
                "status": "indexed",
                "chunk_count": indexing.get("chunk_count", 0),
            }
        except (policy_document_text.PolicyDocumentExtractionError, policy_assistant_client.PolicyAssistantError) as exc:
            # Keep the approved source document durable even when the optional
            # assistant is offline or a legacy/scanned file has no text layer.
            response["assistant_indexing"] = {"status": "unavailable", "message": str(exc)}
        return response
    except UploadTooLargeError as exc:
        db.rollback()
        if stored_path is not None and not committed:
            try:
                storage_service.delete_storage_path(stored_path)
            except storage_service.StorageError:
                pass
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        if stored_path is not None and not committed:
            try:
                storage_service.delete_storage_path(stored_path)
            except storage_service.StorageError:
                pass
        _policy_error(exc)
    finally:
        file.file.close()
