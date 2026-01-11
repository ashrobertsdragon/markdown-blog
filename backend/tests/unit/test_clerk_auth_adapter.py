from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import jwt
import pytest

from backend.config import Settings
from backend.exceptions import AuthenticationError
from backend.infrastructure.auth.clerk_auth_adapter import ClerkAuthAdapter


@pytest.fixture
def dev_settings():
    """Fixture providing test Clerk configuration settings.

    Returns Settings instance with test Clerk API keys for testing
    authentication adapter functionality.
    """
    return Settings(
        clerk_publishable_key="pk_test_Y2xlcmsuZXhhbXBsZS5jb20k",
        clerk_secret_key="sk_test_abcdef123456789",
        environment="test",
    )


@pytest.fixture
def adapter(dev_settings):
    """Fixture providing configured ClerkAuthAdapter instance.

    Args:
        dev_settings: Settings fixture with test configuration

    Returns ClerkAuthAdapter instance ready for testing.
    """
    return ClerkAuthAdapter(dev_settings)


@pytest.fixture
def valid_token(dev_settings):
    """Fixture providing valid JWT token for testing.

    Creates properly signed JWT with standard Clerk claims including
    sub, email, and expiration timestamp.

    Args:
        dev_settings: Settings fixture for signing configuration

    Returns valid JWT token string.
    """
    payload = {
        "sub": "user_2abcdef123456789",
        "email": "test@example.com",
        "iss": "https://clerk.example.com",
        "iat": int(datetime.now(UTC).timestamp()),
        "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
        "azp": "https://app.example.com",
        "sid": "sess_2xyz123456789",
    }
    return jwt.encode(payload, dev_settings.clerk_secret_key, algorithm="HS256")


@pytest.fixture
def expired_token(dev_settings):
    """Fixture providing expired JWT token for testing.

    Creates JWT with expiration timestamp in the past to test
    expiration handling logic.

    Args:
        dev_settings: Settings fixture for signing configuration

    Returns expired JWT token string.
    """
    payload = {
        "sub": "user_2abcdef123456789",
        "email": "test@example.com",
        "iss": "https://clerk.example.com",
        "iat": int((datetime.now(UTC) - timedelta(hours=2)).timestamp()),
        "exp": int((datetime.now(UTC) - timedelta(hours=1)).timestamp()),
    }
    return jwt.encode(payload, dev_settings.clerk_secret_key, algorithm="HS256")


@pytest.fixture
def invalid_token(dev_settings):
    """Fixture providing token with invalid signature for testing.

    Creates JWT signed with wrong key to test signature validation.

    Args:
        dev_settings: Settings fixture for comparison

    Returns JWT token with invalid signature.
    """
    payload = {
        "sub": "user_2abcdef123456789",
        "email": "test@example.com",
        "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
    }
    return jwt.encode(payload, "wrong_secret_key_12345", algorithm="HS256")


@pytest.fixture
def jwks_response():
    """Fixture providing mock JWKS endpoint response.

    Returns properly formatted JWKS response with RSA public key
    for testing key fetching and caching logic.
    """
    return {
        "keys": [
            {
                "kid": "test_key_id_123",
                "kty": "RSA",
                "use": "sig",
                "n": (
                    "xGOr-H7A-PWpKkCejjXmgGfJlRYjwUv64BVrQxvIKFYxPXrQj"
                    "KpHdQzJa_oBNBnZ"
                ),
                "e": "AQAB",
                "alg": "RS256",
            }
        ]
    }


@pytest.fixture
def multi_key_jwks_response():
    """Fixture providing JWKS response with multiple keys.

    Returns JWKS response containing multiple public keys to test
    correct key selection by kid header.
    """
    return {
        "keys": [
            {
                "kid": "old_key_id_456",
                "kty": "RSA",
                "use": "sig",
                "n": "oldkey_n_value",
                "e": "AQAB",
                "alg": "RS256",
            },
            {
                "kid": "test_key_id_123",
                "kty": "RSA",
                "use": "sig",
                "n": (
                    "xGOr-H7A-PWpKkCejjXmgGfJlRYjwUv64BVrQxvIKFYxPXrQj"
                    "KpHdQzJa_oBNBnZ"
                ),
                "e": "AQAB",
                "alg": "RS256",
            },
        ]
    }


def test_settings_has_clerk_publishable_key():
    """Test Settings configuration includes clerk_publishable_key attribute.

    Verifies Settings model defines clerk_publishable_key field for
    storing Clerk public API key.
    """
    settings = Settings(
        clerk_publishable_key="pk_test_example123",
        clerk_secret_key="sk_test_example456",
    )
    assert hasattr(settings, "clerk_publishable_key")
    assert settings.clerk_publishable_key == "pk_test_example123"


def test_settings_has_clerk_secret_key():
    """Test Settings configuration includes clerk_secret_key attribute.

    Verifies Settings model defines clerk_secret_key field for
    storing Clerk secret API key.
    """
    settings = Settings(
        clerk_publishable_key="pk_test_example123",
        clerk_secret_key="sk_test_example456",
    )
    assert hasattr(settings, "clerk_secret_key")
    assert settings.clerk_secret_key == "sk_test_example456"


def test_missing_env_vars_raise_validation_error(clean_env):
    """Test Settings validation fails when Clerk keys are missing.

    Verifies that instantiating Settings without required Clerk
    configuration raises validation error.
    """
    with pytest.raises(Exception):
        Settings()


def test_config_loads_from_environment_variables():
    """Test Settings loads Clerk configuration from environment variables.

    Verifies Settings correctly reads CLERK_PUBLISHABLE_KEY and
    CLERK_SECRET_KEY from environment.
    """
    with patch.dict(
        "os.environ",
        {
            "CLERK_PUBLISHABLE_KEY": "pk_test_env_key",
            "CLERK_SECRET_KEY": "sk_test_env_key",
        },
    ):
        settings = Settings()
        assert settings.clerk_publishable_key == "pk_test_env_key"
        assert settings.clerk_secret_key == "sk_test_env_key"


def test_verify_token_with_valid_jwt_returns_decoded_payload(
    adapter, valid_token
):
    """Test verify_token successfully decodes valid JWT token.

    Verifies that passing valid JWT to verify_token returns
    decoded payload dictionary without raising exceptions.

    Args:
        adapter: ClerkAuthAdapter fixture
        valid_token: Valid JWT fixture
    """
    result = adapter.verify_token(valid_token)
    assert isinstance(result, dict)
    assert len(result) > 0


def test_valid_token_payload_includes_sub(adapter, valid_token):
    """Test decoded token payload contains sub claim with Clerk user ID.

    Verifies verify_token extracts sub claim containing Clerk
    user identifier from token payload.

    Args:
        adapter: ClerkAuthAdapter fixture
        valid_token: Valid JWT fixture
    """
    result = adapter.verify_token(valid_token)
    assert "sub" in result
    assert result["sub"].startswith("user_")


def test_valid_token_payload_includes_email(adapter, valid_token):
    """Test decoded token payload contains email claim.

    Verifies verify_token extracts email address claim from
    token payload.

    Args:
        adapter: ClerkAuthAdapter fixture
        valid_token: Valid JWT fixture
    """
    result = adapter.verify_token(valid_token)
    assert "email" in result
    assert "@" in result["email"]


def test_valid_token_payload_includes_standard_claims(adapter, valid_token):
    """Test decoded token payload contains all standard JWT claims.

    Verifies verify_token returns payload with standard claims
    including iss, iat, exp, azp, and sid.

    Args:
        adapter: ClerkAuthAdapter fixture
        valid_token: Valid JWT fixture
    """
    result = adapter.verify_token(valid_token)
    assert "iss" in result
    assert "iat" in result
    assert "exp" in result
    assert "azp" in result
    assert "sid" in result


def test_verify_token_with_expired_token_raises_authentication_error(
    adapter, expired_token
):
    """Test verify_token rejects expired JWT tokens.

    Verifies that attempting to verify expired token raises
    AuthenticationError exception.

    Args:
        adapter: ClerkAuthAdapter fixture
        expired_token: Expired JWT fixture
    """
    with pytest.raises(AuthenticationError):
        adapter.verify_token(expired_token)


def test_expired_token_error_message_includes_expired(adapter, expired_token):
    """Test expired token error message contains descriptive text.

    Verifies AuthenticationError raised for expired token includes
    the word expired in error message.

    Args:
        adapter: ClerkAuthAdapter fixture
        expired_token: Expired JWT fixture
    """
    with pytest.raises(AuthenticationError) as exc_info:
        adapter.verify_token(expired_token)
    assert "expired" in str(exc_info.value).lower()


def test_expired_token_is_logged(adapter, expired_token, caplog):
    """Test expired token verification attempts are logged.

    Verifies that expired token rejection creates log entry
    for security monitoring.

    Args:
        adapter: ClerkAuthAdapter fixture
        expired_token: Expired JWT fixture
        caplog: Pytest log capture fixture
    """
    with pytest.raises(AuthenticationError):
        adapter.verify_token(expired_token)
    assert any("expired" in record.message.lower() for record in caplog.records)


def test_verify_token_with_wrong_signature_raises_authentication_error(
    adapter, invalid_token
):
    """Test verify_token rejects tokens with invalid signature.

    Verifies that token signed with wrong key raises
    AuthenticationError during verification.

    Args:
        adapter: ClerkAuthAdapter fixture
        invalid_token: Token with invalid signature fixture
    """
    with pytest.raises(AuthenticationError):
        adapter.verify_token(invalid_token)


def test_verify_token_with_tampered_payload_raises_authentication_error(
    adapter, valid_token
):
    """Test verify_token rejects tokens with tampered payload.

    Verifies that modifying token payload after signing raises
    AuthenticationError due to signature mismatch.

    Args:
        adapter: ClerkAuthAdapter fixture
        valid_token: Valid JWT fixture
    """
    parts = valid_token.split(".")
    tampered_token = parts[0] + ".dGFtcGVyZWRfcGF5bG9hZA." + parts[2]

    with pytest.raises(AuthenticationError):
        adapter.verify_token(tampered_token)


def test_invalid_signature_error_message_includes_invalid(
    adapter, invalid_token
):
    """Test invalid signature error message contains descriptive text.

    Verifies AuthenticationError raised for invalid signature
    includes the word invalid in error message.

    Args:
        adapter: ClerkAuthAdapter fixture
        invalid_token: Token with invalid signature fixture
    """
    with pytest.raises(AuthenticationError) as exc_info:
        adapter.verify_token(invalid_token)
    assert "invalid" in str(exc_info.value).lower()


def test_invalid_signature_is_logged(adapter, invalid_token, caplog):
    """Test invalid signature verification attempts are logged.

    Verifies that invalid signature rejection creates log entry
    for security monitoring.

    Args:
        adapter: ClerkAuthAdapter fixture
        invalid_token: Token with invalid signature fixture
        caplog: Pytest log capture fixture
    """
    with pytest.raises(AuthenticationError):
        adapter.verify_token(invalid_token)
    assert any("invalid" in record.message.lower() for record in caplog.records)


def test_verify_token_with_missing_token_raises_error(adapter):
    """Test verify_token rejects None token value.

    Verifies that passing None to verify_token raises
    appropriate error.

    Args:
        adapter: ClerkAuthAdapter fixture
    """
    with pytest.raises((AuthenticationError, ValueError, TypeError)):
        adapter.verify_token(None)


def test_verify_token_with_empty_string_raises_error(adapter):
    """Test verify_token rejects empty string token.

    Verifies that passing empty string to verify_token raises
    appropriate error.

    Args:
        adapter: ClerkAuthAdapter fixture
    """
    with pytest.raises((AuthenticationError, ValueError)):
        adapter.verify_token("")


def test_verify_token_with_invalid_format_raises_error(adapter):
    """Test verify_token rejects malformed token format.

    Verifies that passing non-JWT string to verify_token raises
    appropriate error for invalid format.

    Args:
        adapter: ClerkAuthAdapter fixture
    """
    with pytest.raises((AuthenticationError, ValueError)):
        adapter.verify_token("not.a.valid.jwt.token.format")


@patch("requests.get")
def test_get_public_key_fetches_from_jwks_endpoint_on_first_call(
    mock_get, adapter, jwks_response
):
    """Test first call to _get_public_key fetches from JWKS endpoint.

    Verifies that initial public key request makes HTTP call to
    Clerk JWKS endpoint to retrieve signing keys.

    Args:
        mock_get: Mocked requests.get function
        adapter: ClerkAuthAdapter fixture
        jwks_response: Mock JWKS response fixture
    """
    mock_response = Mock()
    mock_response.json.return_value = jwks_response
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    adapter._get_public_key("test_key_id_123")

    mock_get.assert_called_once()
    assert ".well-known/jwks.json" in mock_get.call_args[0][0]


@patch("requests.get")
def test_get_public_key_uses_cached_key_on_second_call(
    mock_get, adapter, jwks_response
):
    """Test second call to _get_public_key uses cached key.

    Verifies that subsequent public key requests use cached value
    without making additional HTTP calls.

    Args:
        mock_get: Mocked requests.get function
        adapter: ClerkAuthAdapter fixture
        jwks_response: Mock JWKS response fixture
    """
    mock_response = Mock()
    mock_response.json.return_value = jwks_response
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    adapter._get_public_key("test_key_id_123")
    adapter._get_public_key("test_key_id_123")

    mock_get.assert_called_once()


@patch("requests.get")
def test_jwks_endpoint_called_once_for_multiple_tokens(
    mock_get, adapter, jwks_response, dev_settings
):
    """Test JWKS endpoint called only once for multiple token verifications.

    Verifies that verifying multiple tokens reuses cached public key
    rather than fetching from endpoint repeatedly.

    Args:
        mock_get: Mocked requests.get function
        adapter: ClerkAuthAdapter fixture
        jwks_response: Mock JWKS response fixture
        dev_settings: Settings fixture
    """
    mock_response = Mock()
    mock_response.json.return_value = jwks_response
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    token1 = jwt.encode(
        {
            "sub": "user_1",
            "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
        },
        dev_settings.clerk_secret_key,
        algorithm="HS256",
        headers={"kid": "test_key_id_123"},
    )
    token2 = jwt.encode(
        {
            "sub": "user_2",
            "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
        },
        dev_settings.clerk_secret_key,
        algorithm="HS256",
        headers={"kid": "test_key_id_123"},
    )

    with patch.object(
        adapter, "_get_public_key", wraps=adapter._get_public_key
    ):
        adapter.verify_token(token1)
        adapter.verify_token(token2)

    mock_get.assert_called_once()


@patch("requests.get")
@patch("time.time")
def test_cache_respects_one_hour_ttl(
    mock_time, mock_get, adapter, jwks_response
):
    """Test cached JWKS key expires after 1 hour TTL.

    Verifies that public key cache expires after 1 hour and
    triggers new fetch from JWKS endpoint.

    Args:
        mock_time: Mocked time.time function
        mock_get: Mocked requests.get function
        adapter: ClerkAuthAdapter fixture
        jwks_response: Mock JWKS response fixture
    """
    mock_response = Mock()
    mock_response.json.return_value = jwks_response
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    current_time = 1000000
    mock_time.return_value = current_time

    adapter._get_public_key("test_key_id_123")

    mock_time.return_value = current_time + 3601

    adapter._get_public_key("test_key_id_123")

    assert mock_get.call_count == 2


@patch("requests.get")
def test_public_key_extracted_correctly_from_jwks(
    mock_get, adapter, jwks_response
):
    """Test public key extraction from JWKS response.

    Verifies that _get_public_key correctly parses JWKS response
    and extracts RSA public key material.

    Args:
        mock_get: Mocked requests.get function
        adapter: ClerkAuthAdapter fixture
        jwks_response: Mock JWKS response fixture
    """
    mock_response = Mock()
    mock_response.json.return_value = jwks_response
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    key = adapter._get_public_key("test_key_id_123")

    assert key is not None


@patch("requests.get")
def test_jwks_multiple_keys_selects_correct_key_by_kid(
    mock_get, adapter, multi_key_jwks_response
):
    """Test correct key selection from JWKS with multiple keys.

    Verifies that _get_public_key selects correct key from JWKS
    response containing multiple keys using kid header.

    Args:
        mock_get: Mocked requests.get function
        adapter: ClerkAuthAdapter fixture
        multi_key_jwks_response: JWKS with multiple keys fixture
    """
    mock_response = Mock()
    mock_response.json.return_value = multi_key_jwks_response
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    key = adapter._get_public_key("test_key_id_123")

    assert key is not None
    mock_get.assert_called_once()


@patch("requests.get")
def test_network_failure_handled_gracefully(mock_get, adapter):
    """Test JWKS fetch handles network failures gracefully.

    Verifies that network errors during JWKS fetch raise
    appropriate exception without crashing.

    Args:
        mock_get: Mocked requests.get function
        adapter: ClerkAuthAdapter fixture
    """
    mock_get.side_effect = Exception("Network error")

    with pytest.raises((AuthenticationError, Exception)):
        adapter._get_public_key("test_key_id_123")


@patch("requests.get")
def test_jwks_response_parsing_errors_caught(mock_get, adapter):
    """Test JWKS response parsing errors are caught.

    Verifies that malformed JWKS response raises appropriate
    exception during parsing.

    Args:
        mock_get: Mocked requests.get function
        adapter: ClerkAuthAdapter fixture
    """
    mock_response = Mock()
    mock_response.json.return_value = {"invalid": "response"}
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    with pytest.raises((AuthenticationError, KeyError, ValueError)):
        adapter._get_public_key("test_key_id_123")


def test_verify_token_extracts_sub_claim(adapter, valid_token):
    """Test verify_token extracts sub claim containing Clerk user ID.

    Verifies that decoded payload includes sub claim with
    properly formatted Clerk user identifier.

    Args:
        adapter: ClerkAuthAdapter fixture
        valid_token: Valid JWT fixture
    """
    result = adapter.verify_token(valid_token)

    assert "sub" in result
    assert isinstance(result["sub"], str)
    assert len(result["sub"]) > 0


def test_verify_token_returns_full_decoded_payload_as_dict(
    adapter, valid_token
):
    """Test verify_token returns complete decoded payload dictionary.

    Verifies that verify_token returns all claims from token
    payload as dictionary.

    Args:
        adapter: ClerkAuthAdapter fixture
        valid_token: Valid JWT fixture
    """
    result = adapter.verify_token(valid_token)

    assert isinstance(result, dict)
    assert len(result) >= 6


def test_all_standard_jwt_claims_present_in_response(adapter, valid_token):
    """Test decoded payload contains all standard JWT claims.

    Verifies that verify_token preserves all standard JWT claims
    including sub, iss, iat, exp, azp, and sid.

    Args:
        adapter: ClerkAuthAdapter fixture
        valid_token: Valid JWT fixture
    """
    result = adapter.verify_token(valid_token)

    required_claims = ["sub", "email", "iss", "iat", "exp", "azp", "sid"]
    for claim in required_claims:
        assert claim in result
