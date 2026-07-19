"""External-provider minimization and OCR resource-bound regressions."""

from __future__ import annotations

import asyncio
import base64
import io

import pytest
from PIL import Image

from receipt_intelligence_service.config import ReceiptIntelligenceSettings
from receipt_intelligence_service.contracts import ReceiptAnalysisRequest, ReceiptDocumentInput, TextSource
from receipt_intelligence_service.ocr import OcrError, extract_text
from receipt_intelligence_service.providers import ResilientReceiptProvider
from receipt_intelligence_service.service import ReceiptIntelligenceService


class _Repository:
    def observe(self, *_args):
        from receipt_intelligence_service.persistence import DigestObservation

        return DigestObservation(duplicate=False, prior_seen_count=0, total_seen_count=1)

    def ping(self):
        return True

    def close(self):
        return None


class _CaptureProvider:
    def __init__(self):
        self.text: str | None = None

    async def extract(self, text: str):
        self.text = text
        from receipt_intelligence_service.contracts import ReceiptEvidence

        return ReceiptEvidence()


def _request(*, consent: bool) -> ReceiptAnalysisRequest:
    return ReceiptAnalysisRequest(
        organization_scope="org:privacy-test",
        external_provider_consent=consent,
        receipt=ReceiptDocumentInput(
            sha256_digest="a" * 64,
            media_type="image/jpeg",
            size_bytes=10,
            text_source=TextSource.CALLER_EXTRACTED,
            supplied_text=(
                "Customer: Ada Lovelace\n"
                "Email: ada@example.com\n"
                "Phone: +1 415 555 1212\n"
                "Card: 4111 1111 1111 1111\n"
                "123 Main Street\n"
                "Merchant: Metro Taxi\nTotal: USD 42.50"
            ),
        ),
    )


def test_external_provider_receives_only_redacted_opted_in_text():
    capture = _CaptureProvider()
    service = ReceiptIntelligenceService(
        _Repository(),
        ReceiptIntelligenceSettings(
            environment="test",
            groq_external_egress_enabled=True,
            groq_max_text_chars=2_000,
        ),
        ResilientReceiptProvider(capture),
    )

    asyncio.run(service.analyze(_request(consent=True)))

    assert capture.text is not None
    assert "ada@example.com" not in capture.text
    assert "4111" not in capture.text
    assert "+1 415" not in capture.text
    assert "Main Street" not in capture.text
    assert "Metro Taxi" in capture.text


def test_external_provider_is_not_called_without_organization_consent():
    capture = _CaptureProvider()
    service = ReceiptIntelligenceService(
        _Repository(),
        ReceiptIntelligenceSettings(environment="test", groq_external_egress_enabled=True),
        ResilientReceiptProvider(capture),
    )

    asyncio.run(service.analyze(_request(consent=False)))

    assert capture.text is None


def test_ocr_rejects_decoded_size_and_pixel_bombs_before_tesseract(monkeypatch):
    with pytest.raises(OcrError, match="size limit"):
        extract_text("A" * 100, max_bytes=10, max_pixels=100, languages="eng")

    image = Image.new("RGB", (20, 20), color="white")
    payload = io.BytesIO()
    image.save(payload, format="PNG")
    encoded = base64.b64encode(payload.getvalue()).decode("ascii")
    monkeypatch.setattr("receipt_intelligence_service.ocr.pytesseract.image_to_string", lambda *_a, **_k: "never")
    with pytest.raises(OcrError, match="pixel limit"):
        extract_text(encoded, max_bytes=1_000_000, max_pixels=100, languages="eng")
