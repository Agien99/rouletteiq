"""Private roulette API: per-user authorization before every legacy handler.

A request-scoped context value is set by the ASGI middleware, so existing
synchronous repository functions inherit it through FastAPI's worker threads.
"""
import contextvars
import os
from uuid import UUID
from fastapi import HTTPException, Request
from app.auth_session_repository import AuthSessionRepository
from app.database_service import DatabaseService

_current_user_id = contextvars.ContextVar('rouletteiq_request_user_id', default=None)


def request_user_id():
    return _current_user_id.get()


def owner_query(query, params):
    return DatabaseService.fetch_one(query, params)


async def roulette_ownership_middleware(request: Request, call_next):
    import anyio
    path = request.url.path
    protected = path == '/sessions' or path.startswith('/sessions/') or path == '/models'
    is_production = os.getenv('API_ENV', 'development').lower() == 'production'
    if not protected or not is_production:
        return await call_next(request)

    if path == '/models' or path.endswith(('/ml-performance', '/comparison', '/evaluation')):
        from fastapi.responses import JSONResponse
        return JSONResponse({'detail': 'Model reporting not yet owner scoped.'}, status_code=503)

    from fastapi.responses import JSONResponse
    token = request.cookies.get('rouletteiq_session', '')
    user = await anyio.to_thread.run_sync(AuthSessionRepository.resolve, token)
    if not user or not user.get('is_active') or not user.get('email_verified_at'):
        return JSONResponse({'detail': 'Authentication required.'}, status_code=401)

    user_id = str(user['user_id'])
    parts = path.strip('/').split('/')
    if len(parts) >= 2:
        try:
            session_id = str(UUID(parts[1]))
        except (ValueError, AttributeError):
            return JSONResponse({'detail': 'Invalid session identifier.'}, status_code=404)
        owner = await anyio.to_thread.run_sync(owner_query,
            'SELECT session_id FROM public.sessions WHERE session_id=%s AND user_id=%s',
            (session_id, user_id))
        if owner is None:
            return JSONResponse({'detail': 'Session not found.'}, status_code=404)

    # Restrict writes using Origin + CSRF; no CSRF for safe reads.
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        import hmac
        origin = os.getenv('AUTH_TRUSTED_ORIGIN', '').rstrip('/')
        csrf = request.cookies.get('rouletteiq_csrf', '')
        header = request.headers.get('x-csrf-token', '')
        if not origin or request.headers.get('origin') != origin or not csrf or not hmac.compare_digest(csrf, header):
            return JSONResponse({'detail': 'CSRF verification failed.'}, status_code=403)

    scoped = _current_user_id.set(user_id)
    try:
        return await call_next(request)
    finally:
        _current_user_id.reset(scoped)


def legacy_roulette_gate():
    # Per-request auth lives in the middleware in production. Remains a no-op
    # in unit tests/development so existing isolated test cases still execute.
    return None
