from unittest.mock import MagicMock, patch
import pytest
from app.auth_recovery import AuthRecovery, RecoveryError

def test_reject_empty_reset_token():
    with pytest.raises(RecoveryError):
        AuthRecovery.redeem_reset('', 'ValidPassword123!')

def test_reject_oversized_reset_token():
    with pytest.raises(RecoveryError):
        AuthRecovery.redeem_reset('x'*513, 'ValidPassword123!')

def test_password_validation_happens_before_db():
    with patch('app.auth_recovery.DatabaseConfig.get_connection') as db:
        with pytest.raises(ValueError):
            AuthRecovery.redeem_reset('token', 'short')
        db.assert_not_called()

def test_unknown_email_does_not_create_reset():
    with patch('app.user_repository.UserRepository.get_by_email',return_value=None):
        assert AuthRecovery.issue_reset('unknown@example.com') is None
