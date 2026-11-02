"""One-use password reset and email verification tokens."""
from datetime import datetime, timedelta, timezone
from app.auth_security import generate_secure_token, hash_token, hash_password
from app.database import DatabaseConfig

class RecoveryError(ValueError):
    pass

class AuthRecovery:
    @staticmethod
    def issue_reset(email):
        """Return token to trusted delivery layer; never include in public response."""
        from app.user_repository import UserRepository
        user = UserRepository.get_by_email(email)
        if not user or not user['is_active'] or not user.get('password_hash'):
            return None
        token = generate_secure_token()
        with DatabaseConfig.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""INSERT INTO public.password_reset_tokens (user_id,token_hash,expires_at)
                                  VALUES (%s,%s,%s)""", (user['user_id'], hash_token(token),datetime.now(timezone.utc)+timedelta(minutes=30)))
        return token

    @staticmethod
    def redeem_reset(token, password):
        if not token or len(token)>512: raise RecoveryError('Invalid reset link.')
        digest=hash_password(password)
        with DatabaseConfig.get_connection() as conn:
            with conn.transaction():
                with conn.cursor() as cursor:
                    cursor.execute("""SELECT reset_id,user_id FROM public.password_reset_tokens
                                      WHERE token_hash=%s AND used_at IS NULL AND expires_at>NOW() FOR UPDATE""",(hash_token(token),))
                    row=cursor.fetchone()
                    if not row: raise RecoveryError('Invalid reset link.')
                    cursor.execute("""UPDATE public.users SET password_hash=%s,updated_at=NOW()
                                      WHERE user_id=%s AND is_active=TRUE RETURNING user_id""",(digest,row[1]))
                    if not cursor.fetchone(): raise RecoveryError('Account unavailable.')
                    cursor.execute('UPDATE public.password_reset_tokens SET used_at=NOW() WHERE reset_id=%s',(row[0],))
                    cursor.execute('UPDATE public.auth_sessions SET revoked_at=NOW() WHERE user_id=%s AND revoked_at IS NULL',(row[1],))
