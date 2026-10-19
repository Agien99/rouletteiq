from unittest.mock import patch

import pytest

from app.user_repository import UserRepository


def test_normalize_email():
    result = UserRepository.normalize_email(
        "  ADMIN@EXAMPLE.COM  "
    )

    assert result == "admin@example.com"


@pytest.mark.parametrize(
    "email",
    [
        "",
        "invalid-email",
        "first@@example.com",
        "invalid email@example.com",
    ],
)
def test_reject_invalid_emails(email):
    with pytest.raises(ValueError):
        UserRepository.normalize_email(email)


def test_create_user_defaults_to_user_role():
    user = {
        "user_id": "test-user-id",
        "role": "user",
        "email": "test@example.com",
    }

    with patch(
        "app.user_repository."
        "DatabaseService.execute_returning_one",
        return_value=user,
    ) as execute:
        result = UserRepository.create_user(
            full_name="Test User",
            email="TEST@example.com",
            password_hash="hashed-password",
        )

    assert result["role"] == "user"

    query = execute.call_args.args[0]
    params = execute.call_args.args[1]

    assert "'user'" in query
    assert params[1] == "test@example.com"


def test_invalid_user_name():
    with pytest.raises(ValueError):
        UserRepository.create_user(
            full_name="   ",
            email="test@example.com",
            password_hash="hashed-password",
        )


def test_profile_lookup_excludes_password():
    with patch(
        "app.user_repository."
        "DatabaseService.fetch_one",
        return_value=None,
    ) as fetch:
        UserRepository.get_by_id(
            "test-user-id"
        )

    query = fetch.call_args.args[0]

    assert "password_hash" not in query