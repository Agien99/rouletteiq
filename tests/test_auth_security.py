
import pytest

from app.auth_security import (
    generate_secure_token,
    hash_password,
    hash_token,
    needs_password_rehash,
    verify_password,
)


def test_password_hashing():
    password = "ExampleSecurePassword123!"

    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password(
        "IncorrectPassword123!",
        hashed,
    )


def test_password_minimum_length():
    with pytest.raises(ValueError):
        hash_password("short")


def test_invalid_password_hash():
    assert not verify_password(
        "ExampleSecurePassword123!",
        "invalid-hash",
    )


def test_secure_token_generation():
    first = generate_secure_token()
    second = generate_secure_token()

    assert first != second
    assert len(first) >= 32


def test_token_hashing():
    token = generate_secure_token()

    assert hash_token(token) != token
    assert len(hash_token(token)) == 64
    assert hash_token(token) == hash_token(token)


def test_password_rehash_check():
    hashed = hash_password(
        "ExampleSecurePassword123!"
    )

    assert not needs_password_rehash(hashed)