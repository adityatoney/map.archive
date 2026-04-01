"""Authentication tests."""

import pytest
from app.utils.auth import hash_password, verify_password, create_access_token


def test_password_hashing():
    """Password hash and verify roundtrip."""
    password = "demo123"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong", hashed)


def test_create_access_token():
    """JWT token creation should return a string."""
    token = create_access_token(data={"sub": "test@example.com"})
    assert isinstance(token, str)
    assert len(token) > 20
