"""Bounded upload readers used before storage backends receive file bytes."""

from __future__ import annotations

from tempfile import SpooledTemporaryFile

from fastapi import UploadFile


class UploadTooLargeError(ValueError):
    pass


_CHUNK_SIZE = 64 * 1024
_MAX_IN_MEMORY_SPOOL_BYTES = 1024 * 1024


def _declared_length(file: UploadFile) -> int | None:
    value = file.headers.get("content-length") if file.headers else None
    if not value:
        return None
    try:
        parsed = int(value)
    except ValueError as exc:
        raise UploadTooLargeError("Upload Content-Length is invalid") from exc
    if parsed < 0:
        raise UploadTooLargeError("Upload Content-Length is invalid")
    return parsed


async def read_bounded_upload(file: UploadFile, *, max_bytes: int) -> bytes:
    """Read a multipart part in chunks and reject it before unbounded memory use.

    Starlette may already spool multipart bodies, but this guard is still
    required at the application boundary: it rejects a dishonest/missing
    Content-Length after at most one bounded chunk over the configured file
    limit and keeps the intermediate buffer on disk beyond 1 MiB.
    """

    if max_bytes < 1:
        raise ValueError("max_bytes must be positive")
    declared = _declared_length(file)
    if declared is not None and declared > max_bytes:
        raise UploadTooLargeError(f"Upload exceeds the {max_bytes} byte limit")

    total = 0
    with SpooledTemporaryFile(max_size=min(_MAX_IN_MEMORY_SPOOL_BYTES, max_bytes), mode="w+b") as staged:
        while True:
            chunk = await file.read(_CHUNK_SIZE)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise UploadTooLargeError(f"Upload exceeds the {max_bytes} byte limit")
            staged.write(chunk)
        staged.seek(0)
        return staged.read()


def read_bounded_upload_sync(file: UploadFile, *, max_bytes: int) -> bytes:
    """Synchronous counterpart for FastAPI threadpool route handlers.

    ``UploadFile.file`` is Starlette's already-spooled binary stream. Reading
    it in a regular endpoint keeps both disk-backed staging and downstream
    storage/database I/O off the event loop while preserving the same strict
    byte limit as the async helper.
    """

    if max_bytes < 1:
        raise ValueError("max_bytes must be positive")
    declared = _declared_length(file)
    if declared is not None and declared > max_bytes:
        raise UploadTooLargeError(f"Upload exceeds the {max_bytes} byte limit")

    total = 0
    with SpooledTemporaryFile(max_size=min(_MAX_IN_MEMORY_SPOOL_BYTES, max_bytes), mode="w+b") as staged:
        while True:
            chunk = file.file.read(_CHUNK_SIZE)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise UploadTooLargeError(f"Upload exceeds the {max_bytes} byte limit")
            staged.write(chunk)
        staged.seek(0)
        return staged.read()
