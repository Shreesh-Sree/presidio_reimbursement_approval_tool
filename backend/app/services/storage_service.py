"""Configurable, credential-free object storage boundary for uploaded files.

The application stores only metadata in the database.  Bytes are written through
this module, which selects either a local filesystem backend (the default for
development and tests), Appwrite Storage, or an S3 backend configured by the
deployment. Appwrite credentials are server-only configuration and files
remain private; the API's authorization-checked download route is the only
browser gateway.
"""

from __future__ import annotations

import hashlib
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.attachment import Attachment


UploadKind = Literal["policy_document", "receipt"]


POLICY_DOCUMENT_TYPES: dict[str, set[str]] = {
    ".pdf": {"application/pdf"},
    ".doc": {"application/msword"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    },
    ".xls": {"application/vnd.ms-excel"},
    ".xlsx": {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    },
}
RECEIPT_TYPES: dict[str, set[str]] = {
    ".pdf": {"application/pdf"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png": {"image/png"},
    ".webp": {"image/webp"},
}


class UploadValidationError(ValueError):
    """Raised when an upload is not an approved file type or size."""


class StorageError(RuntimeError):
    """Raised when the selected object storage backend cannot serve a file."""


@dataclass(frozen=True)
class StoredObject:
    storage_path: str
    checksum: str
    size_bytes: int


def _safe_file_name(file_name: str) -> str:
    candidate = Path(file_name or "upload").name
    candidate = re.sub(r"[^A-Za-z0-9._-]+", "-", candidate).strip(".-")
    return candidate[:180] or "upload"


def _max_upload_bytes(kind: UploadKind) -> int:
    setting = "MAX_POLICY_DOCUMENT_BYTES" if kind == "policy_document" else "MAX_RECEIPT_BYTES"
    default = 15 * 1024 * 1024 if kind == "policy_document" else 10 * 1024 * 1024
    raw = os.getenv(setting, str(default))
    try:
        configured = int(raw)
    except ValueError as exc:
        raise StorageError(f"{setting} must be an integer number of bytes") from exc
    if configured <= 0:
        raise StorageError(f"{setting} must be greater than zero")
    return configured


def _has_expected_signature(extension: str, content: bytes) -> bool:
    """Perform a small, dependency-free signature check in addition to MIME.

    It is intentionally not a malware scanner; deployment storage should still
    be paired with an antivirus/quarantine service.  It does stop a simple
    renamed text executable from passing an extension-only validation check.
    """

    if extension == ".pdf":
        return content.startswith(b"%PDF-")
    if extension in {".jpg", ".jpeg"}:
        return content.startswith(b"\xff\xd8\xff")
    if extension == ".png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if extension == ".webp":
        return len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP"
    if extension in {".docx", ".xlsx"}:
        return content.startswith(b"PK\x03\x04")
    if extension in {".doc", ".xls"}:
        return content.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")
    return False


def validate_upload(kind: UploadKind, file_name: str, mime_type: str | None, content: bytes) -> str:
    """Validate both extension and browser-declared MIME type before storage."""

    cleaned_name = _safe_file_name(file_name)
    extension = Path(cleaned_name).suffix.lower()
    allowed = POLICY_DOCUMENT_TYPES if kind == "policy_document" else RECEIPT_TYPES
    if extension not in allowed:
        raise UploadValidationError(f"File type {extension or 'unknown'} is not allowed for {kind.replace('_', ' ')}")

    normalized_mime = (mime_type or "").lower().split(";", 1)[0].strip()
    if normalized_mime not in allowed[extension]:
        raise UploadValidationError("The file MIME type does not match an allowed file type")

    max_bytes = _max_upload_bytes(kind)
    if not content:
        raise UploadValidationError("The uploaded file is empty")
    if len(content) > max_bytes:
        raise UploadValidationError(f"The uploaded file exceeds the {max_bytes} byte limit")
    if not _has_expected_signature(extension, content):
        raise UploadValidationError("The uploaded bytes do not match the declared file type")
    return cleaned_name


class LocalStorage:
    def __init__(self, root: Path | None = None):
        self.root = (root or Path(os.getenv("LOCAL_STORAGE_PATH", ".local-storage"))).expanduser().resolve()

    def put(self, key: str, content: bytes) -> str:
        target = (self.root / key).resolve()
        if self.root != target and self.root not in target.parents:
            raise StorageError("Refusing to write outside the local storage directory")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return f"local://{key}"

    def read(self, storage_path: str) -> bytes:
        key = storage_path.removeprefix("local://")
        target = (self.root / key).resolve()
        if self.root != target and self.root not in target.parents:
            raise StorageError("Refusing to read outside the local storage directory")
        try:
            return target.read_bytes()
        except FileNotFoundError as exc:
            raise StorageError("Uploaded file was not found in local storage") from exc

    def delete(self, storage_path: str) -> None:
        key = storage_path.removeprefix("local://")
        target = (self.root / key).resolve()
        if self.root != target and self.root not in target.parents:
            return
        target.unlink(missing_ok=True)


class S3Storage:
    def __init__(self):
        settings = get_settings()
        if not settings.s3_bucket:
            raise StorageError("S3_BUCKET is required when STORAGE_BACKEND=s3")
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover - dependency is part of production extras
            raise StorageError("boto3 is required when STORAGE_BACKEND=s3") from exc
        self.bucket = settings.s3_bucket
        self.client = boto3.client("s3", region_name=settings.aws_region)

    def put(self, key: str, content: bytes) -> str:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=content)
        return f"s3://{key}"

    def read(self, storage_path: str) -> bytes:
        key = storage_path.removeprefix("s3://")
        try:
            return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()
        except Exception as exc:  # boto exceptions differ across configuration versions
            raise StorageError("Uploaded file was not found in object storage") from exc

    def delete(self, storage_path: str) -> None:
        key = storage_path.removeprefix("s3://")
        self.client.delete_object(Bucket=self.bucket, Key=key)


class AppwriteStorage:
    """Private Appwrite Storage adapter for production uploads."""

    scheme = "appwrite://"

    def __init__(self):
        settings = get_settings()
        missing = [
            name
            for name, value in {
                "APPWRITE_ENDPOINT": settings.appwrite_endpoint,
                "APPWRITE_PROJECT_ID": settings.appwrite_project_id,
                "APPWRITE_API_KEY": settings.appwrite_api_key,
                "APPWRITE_BUCKET_ID": settings.appwrite_bucket_id,
            }.items()
            if not value
        ]
        if missing:
            raise StorageError(f"Appwrite storage is not configured: {', '.join(missing)}")
        try:
            from appwrite.client import Client
            from appwrite.services.storage import Storage
        except ImportError as exc:  # pragma: no cover - production dependency
            raise StorageError("appwrite is required when STORAGE_BACKEND=appwrite") from exc

        client = Client()
        client.set_endpoint(settings.appwrite_endpoint)
        client.set_project(settings.appwrite_project_id)
        client.set_key(settings.appwrite_api_key)
        self.bucket_id = settings.appwrite_bucket_id
        self.client = Storage(client)

    def _file_id(self, storage_path: str) -> str:
        file_id = storage_path.removeprefix(self.scheme)
        if not file_id or "/" in file_id:
            raise StorageError("Invalid Appwrite storage path")
        return file_id

    def put(self, key: str, content: bytes) -> str:
        try:
            from appwrite.id import ID
            from appwrite.input_file import InputFile

            file = self.client.create_file(
                bucket_id=self.bucket_id,
                file_id=ID.unique(),
                file=InputFile.from_bytes(content, _safe_file_name(key)),
                permissions=[],
            )
            return f"{self.scheme}{file.id}"
        except Exception as exc:  # SDK exception types vary by transport version
            raise StorageError("Could not store the uploaded file in Appwrite") from exc

    def read(self, storage_path: str) -> bytes:
        try:
            return bytes(self.client.get_file_download(self.bucket_id, self._file_id(storage_path)))
        except Exception as exc:  # SDK exception types vary by transport version
            raise StorageError("Uploaded file was not found in Appwrite storage") from exc

    def delete(self, storage_path: str) -> None:
        try:
            self.client.delete_file(self.bucket_id, self._file_id(storage_path))
        except Exception as exc:  # delete must surface retention failures to callers
            raise StorageError("Could not delete the uploaded Appwrite file") from exc


def _storage_for_path(storage_path: str):
    if storage_path.startswith("s3://"):
        return S3Storage()
    if storage_path.startswith(AppwriteStorage.scheme):
        return AppwriteStorage()
    return LocalStorage()


def _active_storage():
    backend = os.getenv("STORAGE_BACKEND", "local").lower()
    if backend == "local":
        return LocalStorage()
    if backend == "s3":
        return S3Storage()
    if backend == "appwrite":
        return AppwriteStorage()
    raise StorageError("STORAGE_BACKEND must be one of 'local', 'appwrite', or 's3'")


def _storage_key(entity_type: str, entity_id: uuid.UUID, file_name: str) -> str:
    return f"{entity_type}/{entity_id}/{uuid.uuid4().hex}-{file_name}"


def create_attachment(
    db: Session,
    *,
    entity_type: str,
    entity_id: uuid.UUID,
    uploaded_by: uuid.UUID | str,
    file_name: str,
    mime_type: str,
    content: bytes,
    kind: UploadKind,
) -> Attachment:
    """Write a validated file and add, but do not commit, its metadata record."""

    try:
        uploader_id = uploaded_by if isinstance(uploaded_by, uuid.UUID) else uuid.UUID(str(uploaded_by))
    except ValueError as exc:
        raise StorageError("A valid uploader id is required for attachment metadata") from exc
    safe_name = validate_upload(kind, file_name, mime_type, content)
    storage = _active_storage()
    stored_path = storage.put(_storage_key(entity_type, entity_id, safe_name), content)
    try:
        attachment = Attachment(
            entity_type=entity_type,
            entity_id=entity_id,
            file_name=safe_name,
            original_file_name=safe_name,
            storage_path=stored_path,
            mime_type=mime_type.lower().split(";", 1)[0].strip(),
            file_size_bytes=len(content),
            checksum=hashlib.sha256(content).hexdigest(),
            uploaded_by=uploader_id,
        )
        db.add(attachment)
        db.flush()
        return attachment
    except Exception:
        storage.delete(stored_path)
        raise


def get_attachment(db: Session, attachment_id: str | uuid.UUID) -> Attachment | None:
    try:
        resolved_id = attachment_id if isinstance(attachment_id, uuid.UUID) else uuid.UUID(str(attachment_id))
    except ValueError:
        return None
    return db.scalar(
        select(Attachment).where(Attachment.id == resolved_id, Attachment.is_deleted.is_(False))
    )


def latest_entity_attachment(db: Session, *, entity_type: str, entity_id: uuid.UUID) -> Attachment | None:
    return db.scalar(
        select(Attachment)
        .where(
            Attachment.entity_type == entity_type,
            Attachment.entity_id == entity_id,
            Attachment.is_deleted.is_(False),
        )
        .order_by(Attachment.uploaded_at.desc(), Attachment.created_at.desc())
    )


def attachment_url(attachment: Attachment | str | uuid.UUID | None) -> str | None:
    if attachment is None:
        return None
    attachment_id = attachment.id if isinstance(attachment, Attachment) else attachment
    return f"/api/attachments/{attachment_id}/download"


def attachment_payload(attachment: Attachment) -> dict[str, object]:
    return {
        "id": str(attachment.id),
        "url": attachment_url(attachment),
        "file_name": attachment.original_file_name,
        "mime_type": attachment.mime_type,
        "file_size_bytes": attachment.file_size_bytes,
        "uploaded_at": attachment.uploaded_at.isoformat() if attachment.uploaded_at else None,
    }


def read_attachment(attachment: Attachment) -> bytes:
    return _storage_for_path(attachment.storage_path).read(attachment.storage_path)


def delete_attachment_bytes(attachment: Attachment) -> None:
    delete_storage_path(attachment.storage_path)


def delete_storage_path(storage_path: str) -> None:
    _storage_for_path(storage_path).delete(storage_path)
