import os
from unittest.mock import patch
from uuid import uuid4
from fastapi.testclient import TestClient
from app.api.main import app

os.environ.setdefault("AUTH_TRUSTED_ORIGIN", "http://localhost:5173")
HEADERS = {"origin": "http://localhost:5173"}
client = TestClient(app)


def test_unauthenticated_me():
    with patch("app.api.routers.auth.AuthSessionRepository.resolve", return_value=None):
        assert client.get("/auth/me").status_code == 401


def test_me_with_user():
    user = {"user_id": uuid4(), "email": "tester@example.com", "full_name": "Tester", "role": "user"}
    with patch("app.api.routers.auth.AuthSessionRepository.resolve", return_value=user):
        result = client.get("/auth/me")
    assert result.status_code == 200
    assert result.json()["role"] == "user"


def test_login_failure():
    with patch("app.api.routers.auth.UserRepository.get_by_email", return_value=None):
        result = client.post("/auth/login", json={"email": "tester@example.com", "password": "wrong"}, headers=HEADERS)
    assert result.status_code == 401


def test_register_without_valid_invitation():
    from app.invitation_service import InvitationError
    with patch("app.api.routers.auth.InvitationService.redeem_password_invitation", side_effect=InvitationError("Invalid or expired invitation.")):
        result = client.post("/auth/register", json={"token": "invalid", "email": "tester@example.com", "full_name": "Tester", "password": "LongPassword123!"}, headers=HEADERS)
    assert result.status_code == 400


def test_admin_invitation_requires_login():
    with patch("app.api.routers.auth.AuthSessionRepository.resolve", return_value=None):
        result = client.post("/auth/invitations", json={"email": "tester@example.com"}, headers=HEADERS)
    assert result.status_code in (401, 403, 503)
