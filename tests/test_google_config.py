import pytest
from fastapi import HTTPException
from unittest.mock import patch
from app.api.routers.google_oauth import config


def test_missing_google_configuration_fails_closed():
    with patch.dict('os.environ', {}, clear=True):
        with pytest.raises(HTTPException) as error:
            config()
        assert error.value.status_code == 503
