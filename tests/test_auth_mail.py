from unittest.mock import patch
import pytest
from app.auth_mail import send_security_email


def test_mail_fails_closed_without_configuration():
    with patch.dict('os.environ', {}, clear=True):
        with pytest.raises(RuntimeError):
            send_security_email('test@example.com', 'test', 'https://example.com')
