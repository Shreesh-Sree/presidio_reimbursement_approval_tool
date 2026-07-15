import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test_db")
    os.environ.setdefault("JWT_SECRET", "test-secret-key")
    os.environ.setdefault("S3_BUCKET", "test-bucket")
