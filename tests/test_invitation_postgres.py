import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from psycopg.errors import UniqueViolation

from app.database import DatabaseConfig
from app.invitation_repository import InvitationRepository
from app.invitation_service import (
    InvitationError,
    InvitationService,
)


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_NEON_INTEGRATION") != "1",
    reason="PostgreSQL integration environment required",
)


@pytest.fixture
def invitation_data():
    admin_id = uuid4()
    suffix = uuid4().hex
    admin_email = f"admin-{suffix}@example.com"
    invited_email = f"invited-{suffix}@example.com"

    with DatabaseConfig.get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO public.users (
                    user_id,
                    full_name,
                    email,
                    role,
                    is_active
                )
                VALUES (%s, %s, %s, 'admin', TRUE)
                """,
                (
                    admin_id,
                    "Integration Test Admin",
                    admin_email,
                ),
            )

    invitation = InvitationRepository.create_invitation(
        email=invited_email,
        invited_by=str(admin_id),
    )

    try:
        yield {
            "admin_id": admin_id,
            "admin_email": admin_email,
            "email": invited_email,
            "token": invitation["token"],
            "invitation_id": invitation["invitation_id"],
        }

    finally:
        # Clean up only records created by this test.
        with DatabaseConfig.get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM public.user_invitations
                    WHERE invited_by = %s
                    """,
                    (admin_id,),
                )

                cursor.execute(
                    """
                    DELETE FROM public.users
                    WHERE email IN (%s, %s)
                    """,
                    (admin_email, invited_email),
                )


def redeem(data):
    return InvitationService.redeem_password_invitation(
        token=data["token"],
        email=data["email"],
        full_name="Integration Test User",
        password="SecurePassword123!",
    )


def test_real_database_redemption_and_reuse(invitation_data):
    first = redeem(invitation_data)

    assert first["role"] == "user"
    assert first["email"] == invitation_data["email"]

    with pytest.raises(InvitationError):
        redeem(invitation_data)

    with DatabaseConfig.get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM public.users
                WHERE email = %s
                """,
                (invitation_data["email"],),
            )
            assert cursor.fetchone()[0] == 1

            cursor.execute(
                """
                SELECT accepted_by, accepted_at
                FROM public.user_invitations
                WHERE invitation_id = %s
                """,
                (invitation_data["invitation_id"],),
            )

            accepted_by, accepted_at = cursor.fetchone()

            assert str(accepted_by) == first["user_id"]
            assert accepted_at is not None


def test_duplicate_email_rolls_back_invitation(invitation_data):
    with DatabaseConfig.get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO public.users (
                    full_name,
                    email,
                    role,
                    is_active
                )
                VALUES (%s, %s, 'user', TRUE)
                """,
                (
                    "Existing User",
                    invitation_data["email"],
                ),
            )

    with pytest.raises(UniqueViolation):
        redeem(invitation_data)

    with DatabaseConfig.get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT accepted_at, accepted_by
                FROM public.user_invitations
                WHERE invitation_id = %s
                """,
                (invitation_data["invitation_id"],),
            )

            accepted_at, accepted_by = cursor.fetchone()

            assert accepted_at is None
            assert accepted_by is None


def test_concurrent_redemption_only_one_succeeds(
    invitation_data,
):
    def attempt():
        try:
            return ("success", redeem(invitation_data))
        except InvitationError:
            return ("rejected", None)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(attempt)
            for _ in range(2)
        ]

        results = [
            future.result(timeout=30)
            for future in futures
        ]

    successes = [
        result
        for status, result in results
        if status == "success"
    ]

    rejections = [
        status
        for status, _ in results
        if status == "rejected"
    ]

    assert len(successes) == 1
    assert len(rejections) == 1

    with DatabaseConfig.get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM public.users
                WHERE email = %s
                """,
                (invitation_data["email"],),
            )

            assert cursor.fetchone()[0] == 1