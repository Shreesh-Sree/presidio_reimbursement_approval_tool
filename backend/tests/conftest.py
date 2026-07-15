import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test_db")
os.environ.setdefault("JWT_SECRET", "a-very-long-secret-key-for-testing-at-least-32-bytes-long-definitely")
os.environ.setdefault("S3_BUCKET", "test-bucket")
