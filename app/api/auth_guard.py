"""Fail-closed safeguard for legacy routes pending owner-scoped repository migration."""
import os
from fastapi import HTTPException

def legacy_roulette_gate():
    # Existing /sessions and /models endpoints are not owner-scoped.
    # Do not allow them online with accounts until repository ownership is enforced.
    if os.getenv('AUTH_ENFORCE_LEGACY_GUARD','false').lower()=='true' or os.getenv('API_ENV','development').lower()=='production':
        raise HTTPException(status_code=503,detail='Roulette endpoints temporarily disabled pending per-user isolation.')
