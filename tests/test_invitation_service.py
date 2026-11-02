from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.invitation_service import (
    InvitationError,
    InvitationService,
)


def mock_database_connection():
    """
    Create a mocked PostgreSQL connection
    with the correct context manager behavior.
    """
    connection = MagicMock()

    connection.__enter__.return_value = connection

    cursor = (
        connection.cursor
        .return_value.__enter__
        .return_value
    )

    return connection, cursor


def test_reject_empty_token():
    with pytest.raises(InvitationError):
        InvitationService.redeem_password_invitation(
            token="",
            email="test@example.com",
            full_name="Test User",
            password="SecurePassword123!",
        )


def test_reject_long_token():
    with pytest.raises(InvitationError):
        InvitationService.redeem_password_invitation(
            token="x" * 513,
            email="test@example.com",
            full_name="Test User",
            password="SecurePassword123!",
        )


def test_reject_invalid_email():
    with pytest.raises(ValueError):
        InvitationService.redeem_password_invitation(
            token="valid-token",
            email="invalid-email",
            full_name="Test User",
            password="SecurePassword123!",
        )


def test_reject_invalid_name():
    with pytest.raises(ValueError):
        InvitationService.redeem_password_invitation(
            token="valid-token",
            email="test@example.com",
            full_name="   ",
            password="SecurePassword123!",
        )


def test_reject_weak_password():
    with pytest.raises(ValueError):
        InvitationService.redeem_password_invitation(
            token="valid-token",
            email="test@example.com",
            full_name="Test User",
            password="short",
        )


@pytest.mark.parametrize(
    "invitation_state",
    [
        "missing",
        "expired",
        "accepted",
        "revoked",
        "email_mismatch",
    ],
)
def test_reject_invalid_invitation_state(
    invitation_state,
):
    now = datetime.now(timezone.utc)

    invitation = (
        None
        if invitation_state == "missing"
        else (
            uuid4(),
            (
                "different@example.com"
                if invitation_state == "email_mismatch"
                else "test@example.com"
            ),
            (
                now - timedelta(hours=1)
                if invitation_state == "expired"
                else now + timedelta(hours=1)
            ),
            (
                now
                if invitation_state == "accepted"
                else None
            ),
            (
                now
                if invitation_state == "revoked"
                else None
            ),
        )
    )

    connection, cursor = mock_database_connection()

    cursor.fetchone.return_value = invitation

    with patch(
        "app.invitation_service."
        "DatabaseConfig.get_connection",
        return_value=connection,
    ):
        with pytest.raises(InvitationError):
            InvitationService.redeem_password_invitation(
                token="valid-token",
                email="test@example.com",
                full_name="Test User",
                password="SecurePassword123!",
            )

    # Invalid invitations must not create users.
    executed_queries = [
        call.args[0]
        for call in cursor.execute.call_args_list
    ]

    assert not any(
        "INSERT INTO public.users" in query
        for query in executed_queries
    )


def test_successful_invitation_redemption():
    invitation_id = uuid4()
    user_id = uuid4()

    invitation = (
        invitation_id,
        "test@example.com",
        datetime.now(timezone.utc) + timedelta(hours=1),
        None,
        None,
    )

    user = (
        user_id,
        "Test User",
        "test@example.com",
        "user",
        True,
    )

    connection, cursor = mock_database_connection()

    cursor.fetchone.side_effect = [
        invitation,
        user,
        (invitation_id,),
    ]

    with patch(
        "app.invitation_service."
        "DatabaseConfig.get_connection",
        return_value=connection,
    ):
        result = InvitationService.redeem_password_invitation(
            token="valid-token",
            email="test@example.com",
            full_name="Test User",
            password="SecurePassword123!",
        )

    assert result["user_id"] == str(user_id)
    assert result["full_name"] == "Test User"
    assert result["email"] == "test@example.com"
    assert result["role"] == "user"
    assert result["is_active"] is True

    executed_queries = [
        call.args[0]
        for call in cursor.execute.call_args_list
    ]

    assert any(
        "FOR UPDATE" in query
        for query in executed_queries
    )

    assert any(
        "INSERT INTO public.users" in query
        for query in executed_queries
    )

    assert any(
        "UPDATE public.user_invitations" in query
        for query in executed_queries
    )

    connection.transaction.assert_called_once()


def test_redemption_rejects_failed_invitation_update():
    invitation_id = uuid4()
    user_id = uuid4()

    connection, cursor = mock_database_connection()

    cursor.fetchone.side_effect = [
        (
            invitation_id,
            "test@example.com",
            datetime.now(timezone.utc) + timedelta(hours=1),
            None,
            None,
        ),
        (
            user_id,
            "Test User",
            "test@example.com",
            "user",
            True,
        ),
        None,
    ]

    with patch(
        "app.invitation_service."
        "DatabaseConfig.get_connection",
        return_value=connection,
    ):
        with pytest.raises(InvitationError):
            InvitationService.redeem_password_invitation(
                token="valid-token",
                email="test@example.com",
                full_name="Test User",
                password="SecurePassword123!",
            )

    connection.transaction.assert_called_once()