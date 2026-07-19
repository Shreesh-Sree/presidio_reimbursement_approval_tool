"""LLM-backed grounded answer generation with citation-display fallback."""

from __future__ import annotations

import asyncio
import logging
import re

from .contracts import PolicyCitation


logger = logging.getLogger("policy_assistant.provider")

_DECISION_LANGUAGE = re.compile(
    r"\b(?:approve|reject|deny|pay|reimburse|route|escalate|final\s+decision)\b", re.IGNORECASE
)

_BOUNDARY = (
    "This assistant can only explain indexed policy evidence; it cannot approve, "
    "reject, route, pay, or alter any reimbursement workflow."
)


def fallback_answer(question: str, citations: tuple[PolicyCitation, ...]) -> str:
    """Deterministic citation-display answer used when LLM is unavailable."""
    evidence = "\n".join(
        f"- {citation.excerpt} [{citation.source_chunk_id}]" for citation in citations
    )
    return f"{_BOUNDARY}\n\nRelevant indexed policy evidence:\n{evidence}"


class GroqAnswerProvider:
    """Generate a grounded policy answer via Groq LLM."""

    def __init__(self, *, api_key: str, model: str, timeout_seconds: float) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds

    async def generate(self, question: str, citations: tuple[PolicyCitation, ...]) -> str:
        try:
            from groq import AsyncGroq
        except ImportError as exc:
            raise RuntimeError("Groq SDK not installed") from exc

        evidence_block = "\n".join(
            f"[{i + 1}] {citation.excerpt} (source: {citation.source_chunk_id}, similarity: {citation.similarity})"
            for i, citation in enumerate(citations)
        )

        model = self._model
        base_url = None
        if self._api_key.startswith("nvapi-"):
            base_url = "https://integrate.api.nvidia.com/v1"
            if model == "llama-3.1-8b-instant":
                model = "meta/llama-3.1-8b-instruct"

        client = AsyncGroq(
            api_key=self._api_key,
            base_url=base_url,
            timeout=self._timeout_seconds,
            max_retries=0,
        )
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=(
                    {
                        "role": "system",
                        "content": (
                            "You are a policy assistant that answers questions ONLY using the provided policy evidence. "
                            "Rules:\n"
                            "1. Answer ONLY from the evidence provided below. Never invent information.\n"
                            "2. Cite sources using [N] notation matching the evidence numbers.\n"
                            "3. If the evidence doesn't fully answer the question, say so explicitly.\n"
                            "4. NEVER make approval, rejection, payment, or routing decisions.\n"
                            "5. Keep answers concise and factual.\n"
                            "6. Start your answer directly - no preamble."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Policy Evidence:\n{evidence_block}\n\nQuestion: {question}",
                    },
                ),
                temperature=0,
            )
            content = response.choices[0].message.content
            if not content or not content.strip():
                raise RuntimeError("Empty response from Groq")
            answer = content.strip()
            if _DECISION_LANGUAGE.search(question):
                answer = f"{_BOUNDARY}\n\n{answer}"
            return answer
        finally:
            await client.close()


class ResilientAnswerProvider:
    """Try LLM generation first, fall back to citation display."""

    def __init__(
        self,
        primary: GroqAnswerProvider | None,
        *,
        timeout_seconds: float = 8.0,
        max_attempts: int = 2,
    ) -> None:
        self._primary = primary
        self._timeout_seconds = timeout_seconds
        self._max_attempts = max_attempts

    async def generate(self, question: str, citations: tuple[PolicyCitation, ...]) -> tuple[str, str]:
        """Returns (answer_text, provider_name)."""
        if self._primary is None:
            return fallback_answer(question, citations), "rule_based"

        for attempt in range(1, self._max_attempts + 1):
            try:
                answer = await asyncio.wait_for(
                    self._primary.generate(question, citations),
                    timeout=self._timeout_seconds,
                )
                return answer, "groq"
            except Exception as exc:
                logger.warning(
                    "groq_answer_failed",
                    extra={"attempt": attempt, "error": type(exc).__name__},
                )

        return fallback_answer(question, citations), "rule_based_fallback"


def build_answer_provider(settings) -> ResilientAnswerProvider:
    primary = None
    if getattr(settings, "groq_api_key", None):
        primary = GroqAnswerProvider(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            timeout_seconds=settings.groq_timeout_seconds,
        )
    return ResilientAnswerProvider(
        primary,
        timeout_seconds=getattr(settings, "groq_timeout_seconds", 8.0),
        max_attempts=getattr(settings, "groq_max_attempts", 2),
    )
