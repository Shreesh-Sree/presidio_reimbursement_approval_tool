"""Application service for isolated, deterministic receipt checks."""

from __future__ import annotations

import logging

from .analysis import strip_suspicious_instructions
from .config import ReceiptIntelligenceSettings
from .contracts import (
    DeduplicationResult,
    FindingCode,
    FindingSeverity,
    GuardrailResult,
    OcrDisclosure,
    ReceiptAnalysisRequest,
    ReceiptAnalysisResponse,
    ReceiptEvidence,
    ReceiptFinding,
    TextSource,
)
from .observability import LOGGER_NAME, get_correlation_id
from .persistence import DigestRepository, SqliteDigestRepository
from .providers import ResilientReceiptProvider, build_provider
from .redaction import redact_for_external_provider


logger = logging.getLogger(LOGGER_NAME)


class ReceiptIntelligenceService:
    """Analyze ephemeral metadata/text while persisting only digest observations."""

    def __init__(
        self,
        repository: DigestRepository,
        settings: ReceiptIntelligenceSettings,
        provider: ResilientReceiptProvider,
    ) -> None:
        self._repository = repository
        self._settings = settings
        self._provider = provider

    async def analyze(self, request: ReceiptAnalysisRequest) -> ReceiptAnalysisResponse:
        findings: list[ReceiptFinding] = []
        receipt = request.receipt
        evidence = ReceiptEvidence()
        deduplication: DeduplicationResult | None = None

        media_type_allowed: bool | None = None
        size_within_limit: bool | None = None
        text_source = TextSource.NOT_PROVIDED
        provider_name = "none"

        if receipt is not None:
            media_type_allowed = receipt.media_type in self._settings.allowed_media_types
            size_within_limit = receipt.size_bytes <= self._settings.max_file_bytes
            text_source = receipt.text_source

            if not media_type_allowed:
                findings.append(
                    ReceiptFinding(
                        code=FindingCode.UNSUPPORTED_MEDIA_TYPE,
                        severity=FindingSeverity.ERROR,
                        message="The receipt media type is outside the allowed upload types.",
                        details={"media_type": receipt.media_type},
                    )
                )
            if not size_within_limit:
                findings.append(
                    ReceiptFinding(
                        code=FindingCode.FILE_TOO_LARGE,
                        severity=FindingSeverity.ERROR,
                        message="The receipt exceeds the configured file-size limit.",
                        details={
                            "size_bytes": receipt.size_bytes,
                            "max_file_bytes": self._settings.max_file_bytes,
                        },
                    )
                )

            observation = self._repository.observe(request.organization_scope, receipt.sha256_digest)
            deduplication = DeduplicationResult(
                duplicate_within_organization=observation.duplicate,
                prior_seen_count=observation.prior_seen_count,
                total_seen_count=observation.total_seen_count,
            )
            if observation.duplicate:
                findings.append(
                    ReceiptFinding(
                        code=FindingCode.DUPLICATE_RECEIPT_DIGEST,
                        severity=FindingSeverity.WARNING,
                        message="The same receipt digest has already been observed in this organization.",
                        details={"prior_seen_count": observation.prior_seen_count},
                    )
                )

            if receipt.supplied_text:
                bounded_text = receipt.supplied_text[: self._settings.max_text_chars]
                safe_text, suspicious_line_count = strip_suspicious_instructions(bounded_text)
                if suspicious_line_count:
                    findings.append(
                        ReceiptFinding(
                            code=FindingCode.SUSPICIOUS_EMBEDDED_INSTRUCTION,
                            severity=FindingSeverity.WARNING,
                            message=(
                                "Suspicious instruction-like text was detected and ignored before "
                                "receipt evidence extraction."
                            ),
                            details={"ignored_line_count": suspicious_line_count},
                        )
                    )
                allow_external = (
                    self._settings.groq_external_egress_enabled
                    and request.external_provider_consent
                )
                provider_text = (
                    redact_for_external_provider(
                        safe_text, max_chars=self._settings.groq_max_text_chars
                    )
                    if allow_external
                    else safe_text
                )
                evidence, provider_name = await self._provider.extract(
                    provider_text, allow_external=allow_external
                )

        policy = request.policy
        if (
            policy.expense_amount is not None
            and policy.receipt_required_at_or_above is not None
            and policy.expense_amount >= policy.receipt_required_at_or_above
            and receipt is None
        ):
            amount = f"{policy.expense_amount:.2f}"
            threshold = f"{policy.receipt_required_at_or_above:.2f}"
            findings.append(
                ReceiptFinding(
                    code=FindingCode.RECEIPT_REQUIRED_MISSING,
                    severity=FindingSeverity.WARNING,
                    message="A receipt is required for this expense amount but no receipt metadata was supplied.",
                    details={
                        "expense_amount": amount,
                        "receipt_required_at_or_above": threshold,
                        "currency": policy.currency or "unspecified",
                    },
                )
            )

        response = ReceiptAnalysisResponse(
            event_id=request.event_id,
            correlation_id=get_correlation_id(),
            guardrails=GuardrailResult(
                receipt_present=receipt is not None,
                media_type_allowed=media_type_allowed,
                size_within_limit=size_within_limit,
                max_file_bytes=self._settings.max_file_bytes,
                allowed_media_types=self._settings.allowed_media_types,
            ),
            deduplication=deduplication,
            evidence=evidence,
            ocr=OcrDisclosure(
                performed=text_source == TextSource.SERVICE_OCR,
                available_in_this_service=self._settings.ocr_enabled,
                text_source=text_source,
                message=(
                    "Receipt text was extracted locally for this advisory check only."
                    if text_source == TextSource.SERVICE_OCR
                    else "OCR was not performed; any analyzed text was supplied by a trusted caller."
                ),
            ),
            findings=tuple(findings),
        )
        logger.info(
            "receipt_analysis_completed",
            extra={
                "finding_count": len(findings),
                "duplicate": bool(deduplication and deduplication.duplicate_within_organization),
                "evidence_provider": provider_name,
            },
        )
        return response

    def is_ready(self) -> bool:
        return self._repository.ping()

    def close(self) -> None:
        self._repository.close()


def build_service(settings: ReceiptIntelligenceSettings) -> ReceiptIntelligenceService:
    """Build a service backed by PostgreSQL (production) or SQLite (local dev)."""

    if settings.persistence_backend == "postgresql":
        from .postgres_persistence import PostgresDigestRepository
        repository = PostgresDigestRepository(settings.database_url or "")
    else:
        repository = SqliteDigestRepository(settings.database_path)
    return ReceiptIntelligenceService(
        repository=repository,
        settings=settings,
        provider=build_provider(settings),
    )
