from unittest.mock import patch
from uuid import uuid4

import pytest

from app.auth_security import hash_token
from app.invitation_repository import InvitationRepository


def test_create_invitation():
    admin_id = str(uuid4())

    stored = {
        "invitation_id": uuid4(),
        "email": "test@example.com",
        "invited_by": admin_id,
    }

    with patch(
        "app.invitation_repository."
        "DatabaseService.execute_returning_one",
        return_value=stored,
    ) as execute:
        invitation = InvitationRepository.create_invitation(
            email=" TEST@example.com ",
            invited_by=admin_id,
        )

    assert invitation["email"] == "test@example.com"
    assert invitation["token"]

    query, params = execute.call_args.args

    assert "INSERT INTO" in query
    assert params[0] == "test@example.com"
    assert params[1] == hash_token(invitation["token"])
    assert invitation["token"] != params[1]


def test_invitation_tokens_are_unique():
    admin_id = str(uuid4())

    with patch(
        "app.invitation_repository."
        "DatabaseService.execute_returning_one",
        return_value={"invitation_id": uuid4()},
    ):
        first = InvitationRepository.create_invitation(
            "test@example.com",
            admin_id,
        )
        second = InvitationRepository.create_invitation(
            "test@example.com",
            admin_id,
        )

    assert first["token"] != second["token"]


@pytest.mark.parametrize("hours", [0, -1, 169])
def test_reject_invalid_expiry(hours):
    with pytest.raises(ValueError):
        InvitationRepository.create_invitation(
            "test@example.com",
            str(uuid4()),
            expiry_hours=hours,
        )


def test_reject_invalid_admin_identifier():
    with pytest.raises(ValueError):
        InvitationRepository.create_invitation(
            "test@example.com",
            "invalid-uuid",
        )


def test_valid_invitation_lookup():
    with patch(
        "app.invitation_repository."
        "DatabaseService.fetch_one",
        return_value={"email": "test@example.com"},
    ) as fetch:
        result = InvitationRepository.get_valid_invitation(
            "secure-invitation-token"
        )

    assert result["email"] == "test@example.com"

    query, params = fetch.call_args.args

    assert "accepted_at IS NULL" in query
    assert "revoked_at IS NULL" in query
    assert "expires_at > NOW()" in query
    assert params[0] == hash_token(
        "secure-invitation-token"
    )


def test_empty_invitation_token():
    assert InvitationRepository.get_valid_invitation("") is None


def test_revoke_invitation():
    invitation_id = str(uuid4())

    with patch(
        "app.invitation_repository."
        "DatabaseService.execute_returning_one",
        return_value={
            "invitation_id": invitation_id,
            "revoked_at": "2026-10-19",
        },
    ) as execute:
        result = InvitationRepository.revoke_invitation(
            invitation_id
        )

    assert result["revoked_at"] is not None
    assert execute.call_args.args[1] == (invitation_id,)