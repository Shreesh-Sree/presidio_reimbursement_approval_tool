"""Bounded multipart reading regression coverage."""

from __future__ import annotations

import asyncio
from io import BytesIO

import pytest
from starlette.datastructures import Headers, UploadFile

from app.services.upload_guard import UploadTooLargeError, read_bounded_upload, read_bounded_upload_sync


def test_declared_oversize_upload_is_rejected_before_reading() -> None:
    upload = UploadFile(
        BytesIO(b"x" * 11), filename="receipt.pdf", headers=Headers({"content-length": "11"})
    )

    with pytest.raises(UploadTooLargeError, match="10 byte"):
        asyncio.run(read_bounded_upload(upload, max_bytes=10))


def test_chunked_upload_without_length_is_still_hard_capped() -> None:
    upload = UploadFile(BytesIO(b"x" * 11), filename="receipt.pdf")

    with pytest.raises(UploadTooLargeError, match="10 byte"):
        asyncio.run(read_bounded_upload(upload, max_bytes=10))


def test_sync_threadpool_reader_keeps_the_same_hard_cap() -> None:
    upload = UploadFile(BytesIO(b"x" * 11), filename="receipt.pdf")

    with pytest.raises(UploadTooLargeError, match="10 byte"):
        read_bounded_upload_sync(upload, max_bytes=10)
