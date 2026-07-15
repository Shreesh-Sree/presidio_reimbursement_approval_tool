from __future__ import annotations

import sqlite3

from receipt_intelligence_service.persistence import SqliteDigestRepository


def test_sqlite_store_retains_only_scope_digest_timestamps_and_seen_count(tmp_path):
    database_path = tmp_path / "receipt-intelligence.sqlite3"
    repository = SqliteDigestRepository(database_path)

    repository.observe("org:opaque-123", "c" * 64)
    repository.close()

    connection = sqlite3.connect(database_path)
    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(receipt_digest_observations)").fetchall()
    }
    row = connection.execute(
        "SELECT organization_scope, sha256_digest, seen_count FROM receipt_digest_observations"
    ).fetchone()
    connection.close()

    assert columns == {
        "organization_scope",
        "sha256_digest",
        "first_seen_at",
        "last_seen_at",
        "seen_count",
    }
    assert row == ("org:opaque-123", "c" * 64, 1)
