from __future__ import annotations

from flowforge.core.security import create_access_token, hash_password, verify_password


def test_password_hash_roundtrip() -> None:
    hashed_password = hash_password("strong-pass-123")

    assert verify_password("strong-pass-123", hashed_password)


def test_access_token_contains_subject() -> None:
    token = create_access_token("123e4567-e89b-12d3-a456-426614174000")

    assert isinstance(token, str)
    assert token.count(".") == 2
