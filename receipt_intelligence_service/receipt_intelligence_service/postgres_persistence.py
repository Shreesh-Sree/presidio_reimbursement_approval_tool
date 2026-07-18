"""PostgreSQL digest persistence for production deployments (Supabase)."""

from __future__ import annotations

from datetime import datetime, timezone

from psycopg_pool import ConnectionPool

from .persistence import DigestObservation


class PostgresDigestRepository:
    """Supabase PostgreSQL-backed digest deduplication store."""

    def __init__(self, database_url: str) -> None:
        if not database_url:
            raise ValueError("database_url is required for PostgreSQL persistence")
        self._pool = ConnectionPool(database_url, min_size=1, max_size=4)
        self._create_schema()

    def observe(self, organization_scope: str, sha256_digest: str) -> DigestObservation:
        now = datetime.now(timezone.utc)
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO receipt_digest_observations
                        (organization_scope, sha256_digest, first_seen_at, last_seen_at, seen_count)
                    VALUES (%s, %s, %s, %s, 1)
                    ON CONFLICT (organization_scope, sha256_digest)
                    DO UPDATE SET last_seen_at = EXCLUDED.last_seen_at,
                                  seen_count = receipt_digest_observations.seen_count + 1
                    RETURNING seen_count
                    """,
                    (organization_scope, sha256_digest, now, now),
                )
                row = cur.fetchone()
                total_seen_count = int(row[0])
            conn.commit()
        prior_seen_count = total_seen_count - 1
        return DigestObservation(
            duplicate=prior_seen_count > 0,
            prior_seen_count=prior_seen_count,
            total_seen_count=total_seen_count,
        )

    def ping(self) -> bool:
        with self._pool.connection() as conn:
            conn.execute("SELECT 1")
        return True

    def close(self) -> None:
        self._pool.close()

    def _create_schema(self) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS receipt_digest_observations (
                    organization_scope TEXT NOT NULL,
                    sha256_digest TEXT NOT NULL,
                    first_seen_at TIMESTAMPTZ NOT NULL,
                    last_seen_at TIMESTAMPTZ NOT NULL,
                    seen_count INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY (organization_scope, sha256_digest)
                )
                """
            )
            conn.commit()
