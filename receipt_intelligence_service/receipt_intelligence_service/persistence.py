"""Digest-only persistence owned exclusively by receipt intelligence.

This module never stores receipt text, evidence, filenames, URLs, report IDs,
or any core application records. SQLite holds only the organization scope,
SHA-256 digest, timestamps, and a seen count for duplicate detection.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import threading
from typing import Protocol


@dataclass(frozen=True)
class DigestObservation:
    duplicate: bool
    prior_seen_count: int
    total_seen_count: int


class DigestRepository(Protocol):
    def observe(self, organization_scope: str, sha256_digest: str) -> DigestObservation: ...

    def ping(self) -> bool: ...

    def close(self) -> None: ...


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class InMemoryDigestRepository:
    """Thread-safe test/local repository that retains digest-only observations."""

    def __init__(self) -> None:
        self._rows: dict[tuple[str, str], int] = {}
        self._lock = threading.RLock()

    def observe(self, organization_scope: str, sha256_digest: str) -> DigestObservation:
        with self._lock:
            key = (organization_scope, sha256_digest)
            prior_seen_count = self._rows.get(key, 0)
            total_seen_count = prior_seen_count + 1
            self._rows[key] = total_seen_count
            return DigestObservation(
                duplicate=prior_seen_count > 0,
                prior_seen_count=prior_seen_count,
                total_seen_count=total_seen_count,
            )

    def ping(self) -> bool:
        return True

    def close(self) -> None:
        return None


class SqliteDigestRepository:
    """Durable local repository constrained to an isolated SQLite file."""

    def __init__(self, path: str | Path) -> None:
        if str(path).startswith(("postgresql://", "postgres://")):
            raise ValueError(
                "receipt intelligence must use its own datastore, not the core reimbursement database"
            )
        self._path = str(path)
        if self._path != ":memory:":
            Path(self._path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self._path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._create_schema()

    def observe(self, organization_scope: str, sha256_digest: str) -> DigestObservation:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT seen_count
                FROM receipt_digest_observations
                WHERE organization_scope = ? AND sha256_digest = ?
                """,
                (organization_scope, sha256_digest),
            ).fetchone()
            now = _utc_now()
            if row is None:
                self._connection.execute(
                    """
                    INSERT INTO receipt_digest_observations (
                        organization_scope, sha256_digest, first_seen_at, last_seen_at, seen_count
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (organization_scope, sha256_digest, now, now, 1),
                )
                self._connection.commit()
                return DigestObservation(False, 0, 1)

            prior_seen_count = int(row["seen_count"])
            total_seen_count = prior_seen_count + 1
            self._connection.execute(
                """
                UPDATE receipt_digest_observations
                SET last_seen_at = ?, seen_count = ?
                WHERE organization_scope = ? AND sha256_digest = ?
                """,
                (now, total_seen_count, organization_scope, sha256_digest),
            )
            self._connection.commit()
            return DigestObservation(True, prior_seen_count, total_seen_count)

    def ping(self) -> bool:
        with self._lock:
            self._connection.execute("SELECT 1").fetchone()
            return True

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def _create_schema(self) -> None:
        with self._lock:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS receipt_digest_observations (
                    organization_scope TEXT NOT NULL,
                    sha256_digest TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    seen_count INTEGER NOT NULL,
                    PRIMARY KEY (organization_scope, sha256_digest)
                );
                """
            )
            self._connection.commit()
