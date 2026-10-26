import os
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.auth_guard import legacy_roulette_gate
from app.api.main import app


client = TestClient(app)


def test_legacy_guard_disabled_in_development():
    with patch.dict(
        os.environ,
        {"API_ENV": "development"},
    ):
        assert legacy_roulette_gate() is None


def test_production_models_are_blocked():
    with patch.dict(
        os.environ,
        {"API_ENV": "production"},
    ):
        response = client.get("/models")

    assert response.status_code == 503


def test_production_sessions_require_authentication():
    with patch.dict(
        os.environ,
        {"API_ENV": "production"},
    ):
        response = client.get("/sessions")

    assert response.status_code == 401