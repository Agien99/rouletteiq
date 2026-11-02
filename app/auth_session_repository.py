from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.auth_security import generate_secure_token, hash_token
from app.database_service import DatabaseService


class AuthSessionRepository:
    @staticmethod
    def create(user_id: str, hours: int = 24 * 7) -> str:
        UUID(str(user_id))
        if not 1 <= hours <= 24 * 30:
            raise ValueError("Invalid session duration.")
        token = generate_secure_token()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=hours)
        session = DatabaseService.execute_returning_one(
            """INSERT INTO public.auth_sessions (user_id, token_hash, expires_at)
               VALUES (%s, %s, %s) RETURNING auth_session_id""",
            (str(user_id), hash_token(token), expires_at),
        )
        if not session:
            raise RuntimeError("Could not create authentication session.")
        return token

    @staticmethod
    def resolve(token: str) -> dict | None:
        if not token or len(token) > 512:
            return None
        return DatabaseService.fetch_one(
            """SELECT u.user_id, u.email, u.full_name, u.role, u.is_active,
                      u.email_verified_at, s.auth_session_id
               FROM public.auth_sessions AS s
               JOIN public.users AS u ON u.user_id = s.user_id
               WHERE s.token_hash = %s AND s.expires_at > NOW()
                 AND s.revoked_at IS NULL AND u.is_active = TRUE""",
            (hash_token(token),),
        )

    @staticmethod
    def revoke(token: str) -> None:
        if not token or len(token) > 512:
            return
        DatabaseService.execute(
            """UPDATE public.auth_sessions SET revoked_at = NOW()
               WHERE token_hash = %s AND revoked_at IS NULL""",
            (hash_token(token),),
        )
