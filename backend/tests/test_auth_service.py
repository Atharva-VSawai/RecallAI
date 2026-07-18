import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from application.services.auth_service import AuthService
from domain.exceptions import AuthenticationError
def test_asymmetric_tokens_use_jwks_decoder():
    service = AuthService()
    with patch("application.services.auth_service.settings.supabase_url", "https://project.supabase.co"), \
         patch("application.services.auth_service.jwt.get_unverified_header", return_value={"alg": "RS256"}), \
         patch.object(service, "_decode_with_jwks", return_value={"sub": "user-1", "email": "user@example.com"}):
        user = service.authenticate("signed-token")
    assert user.user_id == "user-1"


def test_hs256_tokens_use_auth_server_not_shared_secret():
    service = AuthService()
    response = SimpleNamespace(status_code=200, json=lambda: {"id": "user-2", "email": "user2@example.com"})
    with patch("application.services.auth_service.settings.supabase_url", "https://project.supabase.co"), \
         patch("application.services.auth_service.settings.supabase_publishable_key", "sb_publishable_test"), \
         patch("application.services.auth_service.jwt.get_unverified_header", return_value={"alg": "HS256"}), \
         patch("application.services.auth_service.httpx.get", return_value=response) as request:
        user = service.authenticate("legacy-token")
    request.assert_called_once()
    assert user.user_id == "user-2"


def test_unknown_signing_algorithm_is_rejected():
    service = AuthService(FakeRepository())
    with patch("application.services.auth_service.settings.supabase_url", "https://project.supabase.co"), \
         patch("application.services.auth_service.jwt.get_unverified_header", return_value={"alg": "none"}):
        with pytest.raises(AuthenticationError, match="Unsupported JWT signing algorithm"):
            service.authenticate("unsigned-token")
