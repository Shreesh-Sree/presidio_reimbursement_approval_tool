"""Ephemeral local OCR adapter. It never writes image bytes or extracted text."""

from __future__ import annotations

import io
import math
from base64 import b64decode

from PIL import Image, UnidentifiedImageError
import pytesseract


class OcrError(RuntimeError):
    pass


def extract_text(
    content_base64: str,
    *,
    max_bytes: int,
    max_pixels: int,
    languages: str,
) -> str:
    # Reject oversized decoded content before allocating the decoded bytes.
    estimated_decoded_bytes = math.ceil(len(content_base64) * 3 / 4)
    if estimated_decoded_bytes > max_bytes:
        raise OcrError("OCR input exceeds the configured size limit")
    try:
        content = b64decode(content_base64, validate=True)
    except ValueError as exc:
        raise OcrError("OCR input is not valid base64 data") from exc
    if not content or len(content) > max_bytes:
        raise OcrError("OCR input exceeds the configured size limit")
    try:
        with Image.open(io.BytesIO(content)) as image:
            if image.width < 1 or image.height < 1 or image.width * image.height > max_pixels:
                raise OcrError("OCR input exceeds the configured pixel limit")
            image.load()
            text = pytesseract.image_to_string(image, lang=languages)
    except (UnidentifiedImageError, OSError) as exc:
        raise OcrError("OCR could not read this receipt image") from exc
    except pytesseract.TesseractNotFoundError as exc:
        raise OcrError("Tesseract is not installed on the receipt-intelligence host") from exc
    return text[:100_000]
