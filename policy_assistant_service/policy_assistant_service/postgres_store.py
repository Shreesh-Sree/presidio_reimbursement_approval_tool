"""PostgreSQL persistence backend for the policy vector store."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Sequence

from psycopg_pool import ConnectionPool

from .vector_store import IndexedChunk, RetrievedChunk, cosine_similarity

logger = logging.getLogger(__name__)


class PostgresPolicyStore:
    """Tenant-scoped vector-like store backed by PostgreSQL with float[] embeddings."""

    def __init__(self, database_url: str) -> None:
        if not database_url:
            raise ValueError("database_url is required for PostgresPolicyStore")
        self._pool = ConnectionPool(database_url, min_size=1, max_size=10)
        self._initialise()

    def _initialise(self) -> None:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS policy_documents (
                        tenant_ref TEXT NOT NULL,
                        policy_version_ref TEXT NOT NULL,
                        document_ref TEXT NOT NULL,
                        content_digest TEXT NOT NULL,
                        injection_flags TEXT[] NOT NULL DEFAULT '{}',
                        indexed_at TIMESTAMPTZ NOT NULL,
                        PRIMARY KEY (tenant_ref, policy_version_ref, document_ref)
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS policy_chunks (
                        chunk_id TEXT PRIMARY KEY,
                        tenant_ref TEXT NOT NULL,
                        policy_version_ref TEXT NOT NULL,
                        document_ref TEXT NOT NULL,
                        chunk_index INTEGER NOT NULL,
                        chunk_text TEXT NOT NULL,
                        embedding DOUBLE PRECISION[] NOT NULL,
                        FOREIGN KEY (tenant_ref, policy_version_ref, document_ref)
                            REFERENCES policy_documents(tenant_ref, policy_version_ref, document_ref)
                            ON DELETE CASCADE
                    )
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_policy_chunks_scope
                        ON policy_chunks (tenant_ref, policy_version_ref, chunk_index)
                """)
            conn.commit()

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

        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM policy_documents
                    WHERE tenant_ref = %s AND policy_version_ref = %s AND document_ref = %s
                    """,
                    (tenant_ref, policy_version_ref, document_ref),
                )
                cur.execute(
                    """
                    INSERT INTO policy_documents (
                        tenant_ref, policy_version_ref, document_ref,
                        content_digest, injection_flags, indexed_at
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        tenant_ref,
                        policy_version_ref,
                        document_ref,
                        content_digest,
                        list(injection_flags),
                        datetime.now(UTC),
                    ),
                )
                if chunks:
                    cur.executemany(
                        """
                        INSERT INTO policy_chunks (
                            chunk_id, tenant_ref, policy_version_ref, document_ref,
                            chunk_index, chunk_text, embedding
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        [
                            (
                                chunk.chunk_id,
                                chunk.tenant_ref,
                                chunk.policy_version_ref,
                                chunk.document_ref,
                                index,
                                chunk.text,
                                list(chunk.embedding),
                            )
                            for index, chunk in enumerate(chunks)
                        ],
                    )
            conn.commit()

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

        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT chunk_id, tenant_ref, policy_version_ref, document_ref,
                           chunk_text, embedding
                    FROM policy_chunks
                    WHERE tenant_ref = %s AND policy_version_ref = %s
                    ORDER BY chunk_id ASC
                    """,
                    (tenant_ref, policy_version_ref),
                )
                rows = cur.fetchall()

        matches: list[RetrievedChunk] = []
        for row in rows:
            chunk_id, t_ref, pv_ref, d_ref, text, embedding = row
            similarity = cosine_similarity(query_embedding, embedding)
            if similarity >= minimum_similarity:
                matches.append(
                    RetrievedChunk(
                        chunk_id=chunk_id,
                        tenant_ref=t_ref,
                        policy_version_ref=pv_ref,
                        document_ref=d_ref,
                        text=text,
                        similarity=similarity,
                    )
                )
        matches.sort(key=lambda match: (-match.similarity, match.chunk_id))
        return tuple(matches[:top_k])

    def is_ready(self) -> bool:
        try:
            with self._pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            return True
        except Exception:
            return False

    def close(self) -> None:
        self._pool.close()
