import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)


_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError(
            "Password must contain at least 12 characters."
        )

    if len(password) > 1024:
        raise ValueError(
            "Password exceeds the maximum length."
        )

    return _password_hasher.hash(password)


def verify_password(
    password: str,
    password_hash: str,
) -> bool:
    try:
        return _password_hasher.verify(
            password_hash,
            password,
        )
    except (
        VerifyMismatchError,
        VerificationError,
        InvalidHashError,
    ):
        return False


def needs_password_rehash(
    password_hash: str,
) -> bool:
    return _password_hasher.check_needs_rehash(
        password_hash
    )


def generate_secure_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()