"""Reset endpoints. Delivery must be configured before use in production."""
import os
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from app.api.routers.auth import require_origin
from app.auth_recovery import AuthRecovery, RecoveryError

router=APIRouter(prefix='/auth',tags=['Authentication'])

class ForgotRequest(BaseModel):
    email: EmailStr
class ResetRequest(BaseModel):
    token: str=Field(min_length=1,max_length=512)
    password: str=Field(min_length=12,max_length=1024)

@router.post('/forgot-password',dependencies=[Depends(require_origin)])
def forgot_password(body:ForgotRequest):
    # Intentionally disabled until an email transport is connected.
    # Never generate tokens without reliably delivering them to verified inboxes.
    if os.getenv('AUTH_EMAIL_DELIVERY_ENABLED','false').lower()!='true':
        raise HTTPException(status_code=503,detail='Password recovery is not configured.')
    # Fail closed: delivery adapter is not implemented in this batch.
    raise HTTPException(status_code=503,detail='Password recovery delivery is not configured.')

@router.post('/reset-password',dependencies=[Depends(require_origin)])
def reset_password(body:ResetRequest):
    try:
        AuthRecovery.redeem_reset(body.token,body.password)
    except (RecoveryError,ValueError) as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc
    return {'success':True}
