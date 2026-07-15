from app.core.security import verify_password, hash_password, create_access_token, decode_token
import pytest


def test_token_encode_decode():
    data = {"sub": "user-123", "email": "user@example.com"}
    token = create_access_token(data)
    decoded = decode_token(token)
    assert decoded["sub"] == "user-123"
    assert decoded["email"] == "user@example.com"


def test_invalid_token():
    assert decode_token("invalid-token") is None


def test_password_verification_rejects_passwordless_oauth_account():
    assert verify_password("correct-horse-battery-staple", None) is False
