"""Google OIDC authorization-code flow with state, PKCE and verified subject."""
import base64
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from app.auth_security import generate_secure_token, hash_token
from app.auth_session_repository import AuthSessionRepository
from app.database import DatabaseConfig
from app.api.routers.auth import set_auth_cookies

router = APIRouter(prefix='/auth/google', tags=['Authentication'])


def config():
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
    redirect_uri = os.getenv('GOOGLE_REDIRECT_URI')
    frontend = os.getenv('AUTH_PUBLIC_FRONTEND_URL', '').rstrip('/')
    if not all((client_id, client_secret, redirect_uri, frontend)):
        raise HTTPException(503, 'Google login is not configured.')
    if os.getenv('API_ENV') == 'production' and (not redirect_uri.startswith('https://') or not frontend.startswith('https://')):
        raise HTTPException(503, 'HTTPS is required.')
    return client_id, client_secret, redirect_uri, frontend


@router.get('/start')
def google_start(invite: str = ''):
    client_id, _, redirect_uri, _ = config()
    if len(invite) > 512:
        raise HTTPException(400, 'Invalid invitation.')
    state = generate_secure_token()
    verifier = secrets.token_urlsafe(64)
    nonce = generate_secure_token()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    with DatabaseConfig.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''INSERT INTO public.google_oauth_states
                 (state_hash,code_verifier,nonce,invitation_hash,expires_at) VALUES (%s,%s,%s,%s,%s)''',
                 (hash_token(state), verifier, nonce, hash_token(invite) if invite else None,
                  datetime.now(timezone.utc)+timedelta(minutes=10)))
    query = urlencode({'client_id':client_id, 'redirect_uri':redirect_uri,'response_type':'code',
        'scope':'openid email profile','state':state,'nonce':nonce,'code_challenge':challenge,
        'code_challenge_method':'S256','prompt':'select_account'})
    return RedirectResponse('https://accounts.google.com/o/oauth2/v2/auth?'+query)


@router.get('/callback')
def google_callback(code: str = '', state: str = '', error: str = ''):
    client_id, client_secret, redirect_uri, frontend = config()
    if error or not code or not state or len(state)>512:
        raise HTTPException(400, 'Google authorization declined.')
    with DatabaseConfig.get_connection() as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute('''SELECT code_verifier,nonce,invitation_hash FROM public.google_oauth_states
                    WHERE state_hash=%s AND used_at IS NULL AND expires_at>NOW() FOR UPDATE''', (hash_token(state),))
                row=cur.fetchone()
                if not row:
                    raise HTTPException(400, 'Invalid or expired Google state.')
                verifier, nonce, invitation_hash = row
                cur.execute('UPDATE public.google_oauth_states SET used_at=NOW() WHERE state_hash=%s',(hash_token(state),))
    try:
        with httpx.Client(timeout=15) as client:
            response=client.post('https://oauth2.googleapis.com/token', data={'code':code,'client_id':client_id,
                 'client_secret':client_secret,'redirect_uri':redirect_uri,'grant_type':'authorization_code',
                 'code_verifier':verifier})
            response.raise_for_status()
            id_token=response.json()['id_token']
            checked=client.get('https://oauth2.googleapis.com/tokeninfo', params={'id_token':id_token})
            checked.raise_for_status()
            identity=checked.json()
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        raise HTTPException(400,'Unable to verify Google identity.') from exc
    if (identity.get('aud')!=client_id or identity.get('iss') not in
       ('accounts.google.com','https://accounts.google.com') or identity.get('nonce')!=nonce
       or identity.get('email_verified') not in ('true',True)):
        raise HTTPException(400, 'Google identity verification failed.')
    subject=identity.get('sub','')
    email=identity.get('email','').strip().lower()
    if not subject or not email:
        raise HTTPException(400,'Google account does not expose verified email.')
    # Do not auto-link existing password accounts by email. A Google identity
    # must be explicitly linked through a separate, authenticated flow.
    with DatabaseConfig.get_connection() as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute('''SELECT u.user_id FROM public.auth_identities i
                    JOIN public.users u ON u.user_id=i.user_id
                    WHERE i.provider='google' AND i.provider_subject=%s AND u.is_active=TRUE''',(subject,))
                found=cur.fetchone()
                if found:
                    user_id=found[0]
                else:
                    if not invitation_hash:
                        raise HTTPException(403,'An invitation is required for Google registration.')
                    cur.execute('''SELECT invitation_id,email FROM public.user_invitations
                        WHERE token_hash=%s AND accepted_at IS NULL AND revoked_at IS NULL
                        AND expires_at>NOW() FOR UPDATE''',(invitation_hash,))
                    invitation=cur.fetchone()
                    if not invitation or invitation[1]!=email:
                        raise HTTPException(403,'Invitation is invalid for this Google account.')
                    cur.execute('SELECT user_id FROM public.users WHERE email=%s',(email,))
                    if cur.fetchone():
                        raise HTTPException(409,'This email is already registered. Sign in using its existing method.')
                    cur.execute('''INSERT INTO public.users(full_name,email,role,is_active,email_verified_at)
                        VALUES (%s,%s,'user',TRUE,NOW()) RETURNING user_id''',
                        ((identity.get('name') or email)[:150],email))
                    user_id=cur.fetchone()[0]
                    cur.execute('''INSERT INTO public.auth_identities(user_id,provider,provider_subject)
                        VALUES (%s,'google',%s)''',(user_id,subject))
                    cur.execute('''UPDATE public.user_invitations SET accepted_at=NOW(),accepted_by=%s
                        WHERE invitation_id=%s''',(user_id,invitation[0]))
    token=AuthSessionRepository.create(str(user_id))
    response=RedirectResponse(frontend+'/',status_code=303)
    set_auth_cookies(response,token)
    return response
