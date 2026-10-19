from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.auth_security import (
    generate_secure_token,
    hash_token,
)
from app.database_service import DatabaseService
from app.user_repository import UserRepository


class InvitationRepository:
    DEFAULT_EXPIRY_HOURS = 48

    @staticmethod
    def create_invitation(
        email: str,
        invited_by: str,
        expiry_hours: int = DEFAULT_EXPIRY_HOURS,
    ) -> dict:
        normalized_email = UserRepository.normalize_email(email)

        # Validate the administrator identifier.
        UUID(str(invited_by))

        if not 1 <= expiry_hours <= 168:
            raise ValueError(
                "Invitation expiry must be between "
                "1 and 168 hours."
            )

        token = generate_secure_token()
        token_digest = hash_token(token)

        expires_at = (
            datetime.now(timezone.utc)
            + timedelta(hours=expiry_hours)
        )

        invitation = DatabaseService.execute_returning_one(
            """
            INSERT INTO public.user_invitations (
                email,
                token_hash,
                invited_by,
                expires_at
            )
            VALUES (%s, %s, %s, %s)
            RETURNING
                invitation_id,
                email,
                invited_by,
                expires_at,
                created_at
            """,
            (
                normalized_email,
                token_digest,
                str(invited_by),
                expires_at,
            ),
        )

        if invitation is None:
            raise RuntimeError(
                "Unable to create invitation."
            )

        # The raw token must only be delivered
        # through an authorized, secure channel.
        return {
            **invitation,
            "token": token,
        }

    @staticmethod
    def get_valid_invitation(token: str) -> dict | None:
        if not token:
            return None

        token_digest = hash_token(token)

        return DatabaseService.fetch_one(
            """
            SELECT
                invitation_id,
                email,
                invited_by,
                expires_at,
                created_at
            FROM public.user_invitations
            WHERE token_hash = %s
              AND accepted_at IS NULL
              AND revoked_at IS NULL
              AND expires_at > NOW()
            """,
            (token_digest,),
        )

    @staticmethod
    def revoke_invitation(
        invitation_id: str,
    ) -> dict | None:
        return DatabaseService.execute_returning_one(
            """
            UPDATE public.user_invitations
            SET revoked_at = NOW()
            WHERE invitation_id = %s
              AND accepted_at IS NULL
              AND revoked_at IS NULL
            RETURNING
                invitation_id,
                email,
                revoked_at
            """,
            (invitation_id,),
        )