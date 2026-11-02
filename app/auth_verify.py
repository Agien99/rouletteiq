"""Verification tokens are one-time hashes stored in PostgreSQL."""
from datetime import datetime, timedelta, timezone
from app.database import DatabaseConfig
from app.auth_security import generate_secure_token, hash_token


class VerificationError(ValueError):
    pass


class VerificationService:
    @staticmethod
    def issue(user_id):
        token = generate_secure_token()
        with DatabaseConfig.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''INSERT INTO public.email_verification_tokens
                    (user_id, token_hash, expires_at) VALUES (%s,%s,%s)''',
                    (user_id, hash_token(token), datetime.now(timezone.utc) + timedelta(hours=24)))
        return token

    @staticmethod
    def redeem(token):
        if not token or len(token) > 512:
            raise VerificationError('Invalid verification link.')
        with DatabaseConfig.get_connection() as conn:
            with conn.transaction():
                with conn.cursor() as cursor:
                    cursor.execute('''SELECT verification_id, user_id FROM public.email_verification_tokens
                        WHERE token_hash=%s AND used_at IS NULL AND expires_at>NOW() FOR UPDATE''',
                        (hash_token(token),))
                    row = cursor.fetchone()
                    if not row:
                        raise VerificationError('Invalid verification link.')
                    cursor.execute('''UPDATE public.users SET email_verified_at=COALESCE(email_verified_at,NOW()),
                        updated_at=NOW() WHERE user_id=%s AND is_active=TRUE RETURNING user_id''', (row[1],))
                    if not cursor.fetchone():
                        raise VerificationError('Account unavailable.')
                    cursor.execute('UPDATE public.email_verification_tokens SET used_at=NOW() WHERE verification_id=%s', (row[0],))
