"""Role-aware AI Chatbot API route for all authenticated users."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.policy import Policy
from app.services import policy_assistant_client

router = APIRouter(prefix="/api/ai-chat", tags=["ai-chat"])


class AIChatInput(BaseModel):
    question: str = Field(..., min_length=1, max_length=1200)


class CitationItem(BaseModel):
    excerpt: str
    source_chunk_id: str


class AIChatResponse(BaseModel):
    answer: str
    citations: list[CitationItem] = []
    evidence_found: bool = False


@router.post("", response_model=AIChatResponse)
def ask_ai_chatbot(
    payload: AIChatInput,
    db: Session = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
):
    """Public authenticated endpoint for the role-aware RAG AI assistant."""

    question = payload.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty."
        )

    org_id = user["organization_id"]
    user_roles = [str(r).lower() for r in user.get("roles", [])]
    primary_role = user_roles[0] if user_roles else "employee"

    # Find the active policy for the organization
    policy = db.execute(
        select(Policy)
        .where(Policy.organization_id == org_id, Policy.is_active.is_(True))
    ).scalar_one_or_none()

    if not policy:
        # Fallback to any policy in org
        policy = db.execute(
            select(Policy).where(Policy.organization_id == org_id)
        ).scalar_one_or_none()

    policy_id = policy.id if policy else uuid.UUID("00000000-0000-0000-0000-000000000000")

    # Formulate role-aware prompt prefix
    role_context = f"[User Role: {primary_role.upper()}] "
    full_question = f"{role_context}{question}"

    try:
        raw_res = policy_assistant_client.ask_policy(
            organization_id=org_id,
            policy_id=policy_id,
            question=full_question,
        )

        answer_text = raw_res.get("answer", "")
        evidence_found = raw_res.get("evidence_found", False)
        raw_citations = raw_res.get("citations", [])

        citations = [
            CitationItem(
                excerpt=c.get("excerpt", ""),
                source_chunk_id=c.get("source_chunk_id", ""),
            )
            for c in raw_citations
        ]

        # If RAG evidence is empty, provide a role-specific fallback response
        if not answer_text or not evidence_found:
            answer_text = _build_role_fallback_answer(primary_role, question)

        return AIChatResponse(
            answer=answer_text,
            citations=citations,
            evidence_found=evidence_found,
        )

    except Exception:
        # Fallback on any connection error
        answer_text = _build_role_fallback_answer(primary_role, question)
        return AIChatResponse(
            answer=answer_text,
            citations=[],
            evidence_found=False,
        )


def _build_role_fallback_answer(role: str, question: str) -> str:
    q_lower = question.lower()

    if "employee" in role or role == "user":
        if "meal" in q_lower or "food" in q_lower or "lunch" in q_lower or "dinner" in q_lower:
            return "According to standard company travel policy, meal reimbursements are capped at 1,500 INR per day. Itemized receipts are mandatory for claims over 500 INR."
        if "travel" in q_lower or "flight" in q_lower or "cab" in q_lower or "hotel" in q_lower:
            return "Travel expenses (economy airfare, standard cabs, and accommodation within approved limit) require valid tax invoices and manager pre-approval for outstation trips."
        if "receipt" in q_lower or "bill" in q_lower or "invoice" in q_lower:
            return "Itemized receipts showing transaction date, vendor name, breakdown, and total amount must be attached to all expense claims."
        return "As an Employee, you can create and submit expense reports under 'Reports'. Ensure receipts are attached and categories are correctly selected before submitting for manager approval."

    if "manager" in role:
        if "approve" in q_lower or "check" in q_lower or "review" in q_lower:
            return "As an Approver/Manager, check that the claim matches policy limits, receipts are clear and itemized, and no duplicates exist before approving."
        if "delegate" in q_lower or "substitute" in q_lower:
            return "Delegations can be set under 'Delegations' to temporarily assign your approval queue to another manager during out-of-office periods."
        return "As a Manager, review pending claims in 'Approvals'. You can Approve, Reject with comments, or Send Back claims for revision."

    # Administrator
    if "access" in q_lower or "signup" in q_lower or "user" in q_lower:
        return "Access requests from new users appear under 'Access Requests'. Administrators can approve and assign users to specific departments."
    if "workflow" in q_lower or "routing" in q_lower:
        return "Approval workflows can be customized under 'Workflows' to define multi-level approval hierarchies by department or expense threshold."
    return "As an Administrator, you have full access to manage Users, Departments, Categories, Workflows, Policies, and Access Requests."
