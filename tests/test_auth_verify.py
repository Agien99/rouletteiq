import pytest
from app.auth_verify import VerificationService, VerificationError


def test_bad_verification_token_is_rejected():
    with pytest.raises(VerificationError):
        VerificationService.redeem('')


def test_oversized_verification_token_is_rejected():
    with pytest.raises(VerificationError):
        VerificationService.redeem('x' * 513)
