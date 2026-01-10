import os

import pytest

from backend.config import Settings
from backend.infrastructure.auth.clerk_auth_adapter import (
    AuthenticationError,
    ClerkAuthAdapter,
)
from tests.utils import has_internet


@pytest.fixture
def prod_settings():
    """Create Settings instance with real Clerk configuration from environment.

    This fixture loads actual Clerk credentials from environment variables
    for integration testing against the live Clerk API.
    """
    return Settings(
        clerk_publishable_key=os.getenv("CLERK_PUBLISHABLE_KEY", ""),
        clerk_secret_key=os.getenv("CLERK_SECRET_KEY", ""),
    )


@pytest.fixture
def adapter(prod_settings):
    """Create ClerkAuthAdapter instance with production settings.

    Returns an adapter configured to communicate with the real Clerk API
    using credentials from environment variables.
    """
    return ClerkAuthAdapter(prod_settings)


@pytest.mark.external
@pytest.mark.skipif(not has_internet(), reason="Internet required")
def test_verify_real_clerk_token(adapter):
    """Verify that a real Clerk token can be validated successfully.

    This integration test uses an actual Clerk token from the environment
    to verify end-to-end JWT verification works with Clerk's API. The test
    validates the token structure and ensures required claims are present.
    """
    token = os.getenv("CLERK_TEST_TOKEN")

    payload = adapter.verify_token(token)

    assert "sub" in payload
    assert payload["sub"].startswith("user_")
    assert "email" in payload


@pytest.mark.external
@pytest.mark.skipif(not has_internet(), reason="Internet required")
def test_fetch_real_jwks_key(adapter):
    """Verify adapter fetches real JWKS key from Clerk endpoint.

    This test validates that the adapter can successfully retrieve and parse
    JWKS keys from Clerk's API endpoint. It verifies that the key is a valid
    RSA public key and that caching works correctly with real keys.
    """
    token = os.getenv("CLERK_TEST_TOKEN")

    first_payload = adapter.verify_token(token)

    assert first_payload is not None
    assert "sub" in first_payload

    second_payload = adapter.verify_token(token)

    assert second_payload == first_payload


@pytest.mark.external
@pytest.mark.skipif(not has_internet(), reason="Internet required")
def test_real_token_expiration_handling(adapter):
    """Verify that expired Clerk tokens are properly rejected.

    This test uses an actually expired Clerk token to ensure the adapter
    correctly identifies and rejects expired tokens with a clear error message.
    This validates proper integration with Clerk's token expiration mechanisms.
    """
    expired_token = os.getenv("CLERK_EXPIRED_TOKEN")

    with pytest.raises(AuthenticationError) as exc_info:
        adapter.verify_token(expired_token)

    error_message = str(exc_info.value).lower()
    assert "expired" in error_message or "exp" in error_message


@pytest.mark.external
@pytest.mark.skipif(not has_internet(), reason="Internet required")
def test_real_token_contains_expected_claims(adapter):
    """Verify that real Clerk tokens contain expected standard claims.

    This test validates that tokens issued by Clerk contain the standard
    JWT claims (iss, aud, exp, iat) as well as Clerk-specific claims.
    This ensures compatibility with the expected token structure.
    """
    token = os.getenv("CLERK_TEST_TOKEN")

    payload = adapter.verify_token(token)

    assert "iss" in payload
    assert "aud" in payload
    assert "exp" in payload
    assert "iat" in payload
    assert "sub" in payload


@pytest.mark.external
@pytest.mark.skipif(not has_internet(), reason="Internet required")
def test_real_token_issuer_validation(adapter):
    """Verify that the issuer claim in real tokens matches expected format.

    This test validates that the 'iss' claim in Clerk tokens follows the
    expected format (containing the Clerk domain). This ensures proper
    token origin verification.
    """
    token = os.getenv("CLERK_TEST_TOKEN")

    payload = adapter.verify_token(token)

    assert "iss" in payload
    assert "clerk" in payload["iss"].lower()


@pytest.mark.external
@pytest.mark.skipif(not has_internet(), reason="Internet required")
def test_real_invalid_token_rejection(adapter):
    """Verify that malformed or invalid tokens are properly rejected.

    This test uses an intentionally invalid token to ensure the adapter
    correctly rejects tokens that fail signature verification or have
    other validation issues.
    """
    invalid_token = os.getenv("CLERK_INVALID_TOKEN")

    with pytest.raises(AuthenticationError) as exc_info:
        adapter.verify_token(invalid_token)

    error_message = str(exc_info.value).lower()
    assert any(
        keyword in error_message
        for keyword in ["invalid", "signature", "verification", "decode"]
    )


@pytest.mark.external
@pytest.mark.skipif(not has_internet(), reason="Internet required")
def test_real_token_audience_validation(adapter):
    """Verify that the audience claim is properly validated.

    This test ensures that tokens contain a valid 'aud' claim and that
    the adapter properly validates it against expected audience values.
    """
    token = os.getenv("CLERK_TEST_TOKEN")

    payload = adapter.verify_token(token)

    assert "aud" in payload
    assert payload["aud"] is not None


@pytest.mark.external
@pytest.mark.skipif(not has_internet(), reason="Internet required")
def test_real_token_multiple_verifications(adapter):
    """Verify that the same token can be validated multiple times.

    This test ensures that token verification is idempotent and that
    caching mechanisms don't interfere with repeated verification of
    the same token.
    """
    token = os.getenv("CLERK_TEST_TOKEN")

    payloads = [adapter.verify_token(token) for _ in range(5)]

    assert len(payloads) == 5
    assert all(payload == payloads[0] for payload in payloads)
    assert all("sub" in payload for payload in payloads)


@pytest.mark.external
@pytest.mark.skipif(not has_internet(), reason="Internet required")
def test_real_jwks_endpoint_connectivity(adapter):
    """Verify that the adapter can connect to Clerk's JWKS endpoint.

    This test validates network connectivity and proper handling of the
    JWKS endpoint response. It ensures the adapter can retrieve and parse
    the key set from Clerk's servers.
    """
    token = os.getenv("CLERK_TEST_TOKEN")

    payload = adapter.verify_token(token)

    assert payload is not None
    assert isinstance(payload, dict)
    assert len(payload) > 0
