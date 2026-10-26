from unittest.mock import patch
from uuid import uuid4
from app.api.auth_guard import _current_user_id
from app.session_repository import SessionRepository


def test_historical_sessions_filtered_for_current_user():
    user_id = str(uuid4())
    token = _current_user_id.set(user_id)
    try:
        with patch('app.session_repository.DatabaseService.fetch_all', return_value=[]) as fetch:
            SessionRepository.get_all_sessions()
        assert 'user_id=%s' in fetch.call_args.args[0]
        assert fetch.call_args.args[1] == (user_id,)
    finally:
        _current_user_id.reset(token)


def test_lookup_scopes_session_id():
    user_id = str(uuid4())
    session_id = str(uuid4())
    token = _current_user_id.set(user_id)
    try:
        with patch('app.session_repository.DatabaseService.fetch_one', return_value=None) as fetch:
            SessionRepository.get_session(session_id)
        assert 'user_id=%s' in fetch.call_args.args[0]
        assert fetch.call_args.args[1] == (session_id, user_id)
    finally:
        _current_user_id.reset(token)
