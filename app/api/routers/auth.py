import hmac
import os

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from psycopg.errors import UniqueViolation

from app.auth_security import verify_password
from app.auth_session_repository import AuthSessionRepository
from app.invitation_repository import InvitationRepository
from app.invitation_service import InvitationError, InvitationService
from app.user_repository import UserRepository

router = APIRouter(prefix="/auth", tags=["Authentication"])
COOKIE_NAME = "rouletteiq_session"
CSRF_COOKIE = "rouletteiq_csrf"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    token: str = Field(min_length=1, max_length=512)
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=12, max_length=1024)


class InvitationRequest(BaseModel):
    email: EmailStr
    expiry_hours: int = Field(default=48, ge=1, le=168)


def require_user(rouletteiq_session: str | None = Cookie(default=None)) -> dict:
    user = AuthSessionRepository.resolve(rouletteiq_session or "")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return user


def require_admin(user: dict = Depends(require_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Administrator required.")
    return user


def require_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    trusted = os.getenv("AUTH_TRUSTED_ORIGIN", "").rstrip("/")
    if not trusted:
        raise HTTPException(status_code=503, detail="Authentication origin not configured.")
    if origin != trusted:
        raise HTTPException(status_code=403, detail="Invalid request origin.")


def require_csrf(request: Request, rouletteiq_csrf: str | None = Cookie(default=None)) -> None:
    require_origin(request)
    supplied = request.headers.get("x-csrf-token", "")
    if not rouletteiq_csrf or not hmac.compare_digest(supplied, rouletteiq_csrf):
        raise HTTPException(status_code=403, detail="CSRF verification failed.")


def set_auth_cookies(response: Response, token: str) -> None:
    from app.auth_security import generate_secure_token
    secure = os.getenv("AUTH_COOKIE_SECURE", "true").lower() == "true"
    response.set_cookie(COOKIE_NAME, token, max_age=604800, httponly=True,
                        secure=secure, samesite="lax", path="/")
    response.set_cookie(CSRF_COOKIE, generate_secure_token(), max_age=604800,
                        httponly=False, secure=secure, samesite="lax", path="/")


@router.post("/login", dependencies=[Depends(require_origin)])
def login(payload: LoginRequest, response: Response):
    # Login is not a cookie-authenticated operation; Origin is restricted separately.
    user = UserRepository.get_by_email(str(payload.email))
    if not user or not user["is_active"] or not user.get("password_hash") or \
       not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    if not user.get("email_verified_at"):
        raise HTTPException(status_code=403, detail="Email verification required.")
    token = AuthSessionRepository.create(str(user["user_id"]))
    set_auth_cookies(response, token)
    return {"user_id": str(user["user_id"]), "email": user["email"],
            "full_name": user["full_name"], "role": user["role"]}


@router.get("/me")
def me(user: dict = Depends(require_user)):
    return {"user_id": str(user["user_id"]), "email": user["email"],
            "full_name": user["full_name"], "role": user["role"]}


@router.post("/logout", dependencies=[Depends(require_csrf)])
def logout(response: Response, rouletteiq_session: str | None = Cookie(default=None)):
    AuthSessionRepository.revoke(rouletteiq_session or "")
    response.delete_cookie(COOKIE_NAME, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return {"success": True}


@router.post("/invitations", status_code=201,
             dependencies=[Depends(require_csrf)])
def create_invitation(payload: InvitationRequest, admin: dict = Depends(require_admin)):
    # This returns a one-time token only to the authenticated administrator.
    invitation = InvitationRepository.create_invitation(
        str(payload.email), str(admin["user_id"]), payload.expiry_hours
    )
    invitation["invitation_id"] = str(invitation["invitation_id"])
    invitation["invited_by"] = str(invitation["invited_by"])
    return invitation


@router.post("/register", status_code=201, dependencies=[Depends(require_origin)])
def register(payload: RegisterRequest):
    try:
        # Intentionally no automatic login: email verification is required.
        return InvitationService.redeem_password_invitation(
            payload.token, str(payload.email), payload.full_name, payload.password
        )
    except InvitationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except UniqueViolation as exc:
        raise HTTPException(status_code=409, detail="Account already exists.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
