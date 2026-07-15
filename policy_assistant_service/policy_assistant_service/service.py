"""Grounded policy retrieval with no permission to change core workflows."""

from __future__ import annotations

import hashlib
import logging
import re

from .config import PolicyAssistantSettings
from .contracts import (
    PolicyAskRequest,
    PolicyAskResponse,
    PolicyCitation,
    PolicyDocumentIndexRequest,
    PolicyDocumentIndexResponse,
)
from .sanitization import chunk_text, safe_excerpt, sanitize_policy_document, validate_question
from .vector_store import IndexedChunk, SQLitePolicyStore, hashed_embedding


class UnsafeQuestionError(ValueError):
    """A query attempted to influence assistant behavior instead of ask about policy."""


class EmptyPolicyDocumentError(ValueError):
    """Sanitization removed all provided policy content."""


_DECISION_LANGUAGE = re.compile(
    r"\b(?:approve|reject|deny|pay|reimburse|route|escalate|final\s+decision)\b", re.IGNORECASE
)


class PolicyAssistantService:
    """Local deterministic RAG implementation; it cannot call or mutate core systems."""

    def __init__(self, settings: PolicyAssistantSettings, store: SQLitePolicyStore | None = None) -> None:
        self.settings = settings
        self.store = store or SQLitePolicyStore(settings.database_path)
        self.logger = logging.getLogger("policy_assistant")

    def index_document(self, request: PolicyDocumentIndexRequest) -> PolicyDocumentIndexResponse:
        if len(request.content) > self.settings.max_document_chars:
            raise ValueError(
                f"document exceeds the configured {self.settings.max_document_chars}-character limit"
            )

        sanitized = sanitize_policy_document(request.content)
        if not sanitized.text:
            raise EmptyPolicyDocumentError(
                "document contained no indexable policy evidence after safety sanitization"
            )

        content_digest = hashlib.sha256(sanitized.text.encode("utf-8")).hexdigest()
        source_digest = hashlib.sha256(
            f"{request.document_ref}\x00{sanitized.text}".encode("utf-8")
        ).hexdigest()
        text_chunks = chunk_text(
            sanitized.text,
            chunk_size=self.settings.chunk_size_chars,
            overlap=self.settings.chunk_overlap_chars,
        )
        indexed_chunks = tuple(
            IndexedChunk(
                chunk_id=f"chunk-{source_digest[:20]}-{index:04d}",
                tenant_ref=request.tenant_ref,
                policy_version_ref=request.policy_version_ref,
                document_ref=request.document_ref,
                text=text,
                embedding=hashed_embedding(text, dimensions=self.settings.embedding_dimensions),
            )
            for index, text in enumerate(text_chunks, start=1)
        )
        self.store.replace_document(
            tenant_ref=request.tenant_ref,
            policy_version_ref=request.policy_version_ref,
            document_ref=request.document_ref,
            content_digest=content_digest,
            injection_flags=sanitized.flags,
            chunks=indexed_chunks,
        )
        self.logger.info(
            "policy document indexed",
            extra={
                "event": "policy_document_indexed",
                "tenant_ref": request.tenant_ref,
                "policy_version_ref": request.policy_version_ref,
                "chunk_count": len(indexed_chunks),
            },
        )
        return PolicyDocumentIndexResponse(
            tenant_ref=request.tenant_ref,
            policy_version_ref=request.policy_version_ref,
            document_ref=request.document_ref,
            document_digest=content_digest,
            chunk_count=len(indexed_chunks),
            injection_flags=sanitized.flags,
        )

    def ask(self, request: PolicyAskRequest) -> PolicyAskResponse:
        if len(request.question) > self.settings.max_question_chars:
            raise ValueError(
                f"question exceeds the configured {self.settings.max_question_chars}-character limit"
            )

        validated_question = validate_question(request.question)
        if validated_question.flags:
            self.logger.warning(
                "unsafe policy question rejected",
                extra={
                    "event": "policy_question_rejected",
                    "tenant_ref": request.tenant_ref,
                    "policy_version_ref": request.policy_version_ref,
                },
            )
            raise UnsafeQuestionError(
                "question contains instruction-like content; ask only about indexed policy evidence"
            )

        top_k = request.top_k or self.settings.default_top_k
        matches = self.store.search(
            tenant_ref=request.tenant_ref,
            policy_version_ref=request.policy_version_ref,
            query_embedding=hashed_embedding(
                validated_question.text, dimensions=self.settings.embedding_dimensions
            ),
            top_k=top_k,
            minimum_similarity=self.settings.minimum_similarity,
        )
        if not matches:
            return PolicyAskResponse(
                answer=(
                    "I do not have sufficient indexed policy evidence to answer that question. "
                    "Please index the applicable policy version or ask a more specific policy question."
                ),
                evidence_found=False,
                citations=(),
            )

        citations = tuple(
            PolicyCitation(
                tenant_ref=match.tenant_ref,
                policy_version_ref=match.policy_version_ref,
                document_ref=match.document_ref,
                source_chunk_id=match.chunk_id,
                excerpt=safe_excerpt(match.text),
                similarity=round(match.similarity, 6),
            )
            for match in matches
        )
        answer = self._grounded_answer(question=validated_question.text, citations=citations)
        self.logger.info(
            "policy evidence retrieved",
            extra={
                "event": "policy_question_answered",
                "tenant_ref": request.tenant_ref,
                "policy_version_ref": request.policy_version_ref,
                "chunk_count": len(citations),
            },
        )
        return PolicyAskResponse(answer=answer, evidence_found=True, citations=citations)

    @staticmethod
    def _grounded_answer(*, question: str, citations: tuple[PolicyCitation, ...]) -> str:
        """Use only retrieved excerpts; no ungrounded narrative or workflow action."""

        boundary = (
            "This assistant can only explain indexed policy evidence; it cannot approve, "
            "reject, route, pay, or alter any reimbursement workflow."
        )
        evidence = "\n".join(
            f"- {citation.excerpt} [{citation.source_chunk_id}]" for citation in citations
        )
        if _DECISION_LANGUAGE.search(question):
            return f"{boundary}\n\nRelevant indexed policy evidence:\n{evidence}"
        return f"{boundary}\n\nRelevant indexed policy evidence:\n{evidence}"

    def is_ready(self) -> bool:
        return self.store.is_ready()
