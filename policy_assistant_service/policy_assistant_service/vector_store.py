"""Small deterministic vector-like index backed by a dedicated SQLite database."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import math
from pathlib import Path
import sqlite3
from typing import Iterator, Sequence


_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "what",
    "with",
}


@dataclass(frozen=True)
class IndexedChunk:
    chunk_id: str
    tenant_ref: str
    policy_version_ref: str
    document_ref: str
    text: str
    embedding: tuple[float, ...]


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    tenant_ref: str
    policy_version_ref: str
    document_ref: str
    text: str
    similarity: float


def _normalise_token(token: str) -> str:
    """A deliberately small normalizer for common policy-question variants."""

    if len(token) > 4 and token.endswith("ies"):
        return f"{token[:-3]}y"
    if len(token) > 4 and token.endswith("ed"):
        stem = token[:-2]
        if len(stem) > 2 and stem[-1] == stem[-2]:
            stem = stem[:-1]
        return stem
    if len(token) > 3 and token.endswith("s"):
        return token[:-1]
    return token


def _tokens(text: str) -> tuple[str, ...]:
    import re

    return tuple(
        normalised
        for token in re.findall(r"[a-z0-9]{2,}", text.lower())
        if (normalised := _normalise_token(token)) not in _STOP_WORDS
    )


def hashed_embedding(text: str, *, dimensions: int) -> tuple[float, ...]:
    """Stable local feature hashing: no model download, cost, or data egress."""

    vector = [0.0] * dimensions
    for token in _tokens(text):
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        value = int.from_bytes(digest, "big")
        index = value % dimensions
        vector[index] += -1.0 if value & 1 else 1.0
    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude == 0:
        return tuple(vector)
    return tuple(value / magnitude for value in vector)


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ValueError("embedding dimensions do not match")
    return sum(a * b for a, b in zip(left, right, strict=True))


class SQLitePolicyStore:
    """A tiny, tenant-scoped document index with no core database dependency."""

    def __init__(self, database_path: str) -> None:
        self.database_path = database_path
        self._memory_connection: sqlite3.Connection | None = None
        if database_path == ":memory:":
            # A keeper connection makes a shared in-memory database durable for
            # the lifetime of one service instance (handy for hermetic tests).
            self._database_target = "file:policy-assistant-memory?mode=memory&cache=shared"
            self._database_uri = True
            self._memory_connection = sqlite3.connect(
                self._database_target, uri=True, check_same_thread=False
            )
        else:
            path = Path(database_path).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)
            self._database_target = str(path)
            self._database_uri = False
        self._initialise()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(
            self._database_target,
            uri=self._database_uri,
            timeout=10,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialise(self) -> None:
        with self._connection() as connection:
            if not self._database_uri:
                connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS policy_documents (
                    tenant_ref TEXT NOT NULL,
                    policy_version_ref TEXT NOT NULL,
                    document_ref TEXT NOT NULL,
                    content_digest TEXT NOT NULL,
                    indexed_at TEXT NOT NULL,
                    injection_flags_json TEXT NOT NULL,
                    PRIMARY KEY (tenant_ref, policy_version_ref, document_ref)
                );

                CREATE TABLE IF NOT EXISTS policy_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    tenant_ref TEXT NOT NULL,
                    policy_version_ref TEXT NOT NULL,
                    document_ref TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    chunk_text TEXT NOT NULL,
                    embedding_json TEXT NOT NULL,
                    FOREIGN KEY (tenant_ref, policy_version_ref, document_ref)
                        REFERENCES policy_documents(tenant_ref, policy_version_ref, document_ref)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_policy_chunks_scope
                    ON policy_chunks (tenant_ref, policy_version_ref, chunk_index);
                """
            )

    def replace_document(
        self,
        *,
        tenant_ref: str,
        policy_version_ref: str,
        document_ref: str,
        content_digest: str,
        injection_flags: tuple[str, ...],
        chunks: Sequence[IndexedChunk],
    ) -> None:
        """Atomically replace one document only inside its tenant/policy boundary."""

        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                DELETE FROM policy_documents
                WHERE tenant_ref = ? AND policy_version_ref = ? AND document_ref = ?
                """,
                (tenant_ref, policy_version_ref, document_ref),
            )
            connection.execute(
                """
                INSERT INTO policy_documents (
                    tenant_ref, policy_version_ref, document_ref, content_digest,
                    indexed_at, injection_flags_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    tenant_ref,
                    policy_version_ref,
                    document_ref,
                    content_digest,
                    datetime.now(UTC).isoformat(),
                    json.dumps(injection_flags),
                ),
            )
            connection.executemany(
                """
                INSERT INTO policy_chunks (
                    chunk_id, tenant_ref, policy_version_ref, document_ref, chunk_index,
                    chunk_text, embedding_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        chunk.chunk_id,
                        chunk.tenant_ref,
                        chunk.policy_version_ref,
                        chunk.document_ref,
                        index,
                        chunk.text,
                        json.dumps(chunk.embedding),
                    )
                    for index, chunk in enumerate(chunks)
                ],
            )

    def search(
        self,
        *,
        tenant_ref: str,
        policy_version_ref: str,
        query_embedding: Sequence[float],
        top_k: int,
        minimum_similarity: float,
    ) -> tuple[RetrievedChunk, ...]:
        """Retrieve only chunks explicitly owned by the request tenant/policy."""

        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT chunk_id, tenant_ref, policy_version_ref, document_ref,
                       chunk_text, embedding_json
                FROM policy_chunks
                WHERE tenant_ref = ? AND policy_version_ref = ?
                ORDER BY chunk_id ASC
                """,
                (tenant_ref, policy_version_ref),
            ).fetchall()

        matches: list[RetrievedChunk] = []
        for row in rows:
            similarity = cosine_similarity(query_embedding, json.loads(row["embedding_json"]))
            if similarity >= minimum_similarity:
                matches.append(
                    RetrievedChunk(
                        chunk_id=row["chunk_id"],
                        tenant_ref=row["tenant_ref"],
                        policy_version_ref=row["policy_version_ref"],
                        document_ref=row["document_ref"],
                        text=row["chunk_text"],
                        similarity=similarity,
                    )
                )
        matches.sort(key=lambda match: (-match.similarity, match.chunk_id))
        return tuple(matches[:top_k])

    def is_ready(self) -> bool:
        try:
            with self._connection() as connection:
                tables = {
                    row["name"]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    ).fetchall()
                }
            return {"policy_documents", "policy_chunks"}.issubset(tables)
        except sqlite3.Error:
            return False
