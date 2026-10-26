import os
from unittest.mock import patch
import pytest
from fastapi import HTTPException
from app.api.auth_guard import legacy_roulette_gate

def test_legacy_guard_disabled_in_development():
    with patch.dict(os.environ,{'API_ENV':'development','AUTH_ENFORCE_LEGACY_GUARD':'false'}):
        assert legacy_roulette_gate() is None

def test_legacy_guard_enabled_in_production():
    with patch.dict(os.environ,{'API_ENV':'production','AUTH_ENFORCE_LEGACY_GUARD':'false'}):
        with pytest.raises(HTTPException) as exc:
            legacy_roulette_gate()
    assert exc.value.status_code==503
