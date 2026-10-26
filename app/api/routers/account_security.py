"""Email verification and password reset, with SMTP delivery."""
import os
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from app.api.routers.auth import require_origin, require_user
from app.auth_verify import VerificationService, VerificationError
from app.auth_mail import send_security_email
from app.auth_recovery import AuthRecovery, RecoveryError
from app.user_repository import UserRepository

router = APIRouter(prefix='/auth', tags=['Authentication'])


class EmailBody(BaseModel):
    email: EmailStr


class TokenBody(BaseModel):
    token: str = Field(min_length=1, max_length=512)


def frontend_url():
    base = os.getenv('AUTH_PUBLIC_FRONTEND_URL', '').rstrip('/')
    if not base.startswith('https://') and os.getenv('API_ENV') == 'production':
        raise HTTPException(503, 'Secure frontend URL not configured')
    if not base:
        raise HTTPException(503, 'Frontend URL not configured')
    return base


@router.post('/request-password-reset', dependencies=[Depends(require_origin)])
def request_password_reset(body: EmailBody):
    # Generic response prevents account enumeration. Never return the token.
    base = frontend_url()
    token = AuthRecovery.issue_reset(str(body.email))
    if token:
        send_security_email(str(body.email), 'RouletteIQ password reset',
                            f'{base}/?reset={quote(token)}')
    return {'message': 'If the account is eligible, a reset email will be sent.'}


@router.post('/request-verification', dependencies=[Depends(require_origin)])
def request_verification(body: EmailBody):
    base = frontend_url()
    user = UserRepository.get_by_email(str(body.email))
    if user and user['is_active'] and not user.get('email_verified_at'):
        token = VerificationService.issue(str(user['user_id']))
        send_security_email(str(body.email), 'Verify your RouletteIQ email',
                            f'{base}/?verify={quote(token)}')
    return {'message': 'If verification is required, an email will be sent.'}


@router.post('/verify-email', dependencies=[Depends(require_origin)])
def verify_email(body: TokenBody):
    try:
        VerificationService.redeem(body.token)
    except VerificationError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {'success': True}
