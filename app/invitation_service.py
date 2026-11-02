from datetime import datetime, timezone

from app.auth_security import hash_password, hash_token
from app.database import DatabaseConfig
from app.user_repository import UserRepository


class InvitationError(ValueError):
    """Invitation cannot be redeemed."""


class InvitationService:
    @staticmethod
    def redeem_password_invitation(
        token: str,
        email: str,
        full_name: str,
        password: str,
    ) -> dict:
        if not token or len(token) > 512:
            raise InvitationError(
                "Invalid or expired invitation."
            )

        normalized_email = (
            UserRepository.normalize_email(email)
        )

        name = full_name.strip()

        if not name or len(name) > 150:
            raise ValueError("Invalid full name.")

        # Hash before opening the transaction,
        # avoiding expensive hashing while
        # holding the invitation row lock.
        password_digest = hash_password(password)
        invitation_digest = hash_token(token)

        with DatabaseConfig.get_connection() as connection:
            with connection.transaction():
                with connection.cursor() as cursor:
                    # Lock invitation until the entire
                    # registration transaction finishes.
                    cursor.execute(
                        """
                        SELECT
                            invitation_id,
                            email,
                            expires_at,
                            accepted_at,
                            revoked_at
                        FROM public.user_invitations
                        WHERE token_hash = %s
                        FOR UPDATE
                        """,
                        (invitation_digest,),
                    )

                    invitation = cursor.fetchone()

                    if invitation is None:
                        raise InvitationError(
                            "Invalid or expired invitation."
                        )

                    (
                        invitation_id,
                        invited_email,
                        expires_at,
                        accepted_at,
                        revoked_at,
                    ) = invitation

                    current_time = datetime.now(
                        timezone.utc
                    )

                    if (
                        accepted_at is not None
                        or revoked_at is not None
                        or expires_at <= current_time
                        or invited_email != normalized_email
                    ):
                        raise InvitationError(
                            "Invalid or expired invitation."
                        )

                    # Registration always creates a
                    # standard user, never an admin.
                    cursor.execute(
                        """
                        INSERT INTO public.users (
                            full_name,
                            email,
                            password_hash,
                            role,
                            is_active,
                            email_verified_at
                        )
                        VALUES (
                            %s, %s, %s,
                            'user', TRUE, NULL
                        )
                        RETURNING
                            user_id,
                            full_name,
                            email,
                            role,
                            is_active
                        """,
                        (
                            name,
                            normalized_email,
                            password_digest,
                        ),
                    )

                    user = cursor.fetchone()

                    if user is None:
                        raise RuntimeError(
                            "Unable to create user."
                        )

                    user_id = user[0]

                    cursor.execute(
                        """
                        UPDATE public.user_invitations
                        SET
                            accepted_at = NOW(),
                            accepted_by = %s
                        WHERE invitation_id = %s
                          AND accepted_at IS NULL
                          AND revoked_at IS NULL
                        RETURNING invitation_id
                        """,
                        (user_id, invitation_id),
                    )

                    if cursor.fetchone() is None:
                        raise InvitationError(
                            "Invitation already used."
                        )

                    return {
                        "user_id": str(user_id),
                        "full_name": user[1],
                        "email": user[2],
                        "role": user[3],
                        "is_active": user[4],
                    }