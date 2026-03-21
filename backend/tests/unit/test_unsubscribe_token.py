"""Unit tests for UnsubscribeToken value object."""

import pytest

from backend.domain.value_objects.unsubscribe_token import UnsubscribeToken


def test_generate_returns_hex_string(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify generate() produces a token whose value is valid lowercase hex.

    The token is transmitted in unsubscribe URLs, so it must be URL-safe
    plain hex. Any non-hex character would break link parsing in email
    clients and prevent successful unsubscribe confirmation.
    """
    monkeypatch.setenv("SECRET_KEY", "test-secret")

    token = UnsubscribeToken.generate(user_id=1, email="user@example.com")

    assert all(c in "0123456789abcdef" for c in token.value)
    assert len(token.value) > 0


def test_verify_returns_true_for_matching_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify verify() accepts a token produced from the same inputs.

    The unsubscribe flow generates a token at send-time and later verifies
    it when the user clicks the link. The same user_id, email, and SECRET_KEY
    must produce a passing verification so legitimate unsubscribes succeed.
    """
    monkeypatch.setenv("SECRET_KEY", "test-secret")

    token = UnsubscribeToken.generate(user_id=1, email="user@example.com")

    assert UnsubscribeToken.verify(
        token.value, user_id=1, email="user@example.com"
    )


def test_verify_returns_false_for_tampered_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify verify() rejects a token string that does not match the inputs.

    An attacker may supply an arbitrary string to unsubscribe a different
    user. verify() must return False for any token that was not produced
    from the given user_id and email, preventing unauthorised unsubscriptions.
    """
    monkeypatch.setenv("SECRET_KEY", "test-secret")

    assert not UnsubscribeToken.verify(
        "deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        user_id=1,
        email="user@example.com",
    )


def test_init_raises_on_none() -> None:
    """Verify UnsubscribeToken rejects None as a raw_token value.

    None is not a string and cannot represent a hex digest. Raising
    TypeError at construction time prevents callers from accidentally
    storing an invalid token and later failing silently during verification.
    """
    with pytest.raises(TypeError):
        UnsubscribeToken(None)  # type: ignore[arg-type]


def test_init_raises_on_empty() -> None:
    """Verify UnsubscribeToken rejects an empty string.

    An empty token string cannot be a valid HMAC digest and would always
    fail verification. Raising ValueError at construction ensures the
    object invariant (non-empty hex value) is enforced at the boundary.
    """
    with pytest.raises(ValueError):
        UnsubscribeToken("")


def test_init_raises_on_non_hex() -> None:
    """Verify UnsubscribeToken rejects strings containing non-hex characters.

    The value object contract requires a lowercase hex HMAC-SHA256 digest.
    Any character outside 0-9 and a-f indicates a corrupted or forged token
    and must be rejected to prevent invalid state from entering the domain.
    """
    with pytest.raises(ValueError):
        UnsubscribeToken("not-hex!!")


def test_two_calls_with_same_inputs_produce_same_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify generate() is deterministic for identical inputs.

    The same user_id, email, and SECRET_KEY must always produce the same
    token so a token generated at email-send time can be reproduced for
    verification without storing the token in the database.
    """
    monkeypatch.setenv("SECRET_KEY", "test-secret")

    token_a = UnsubscribeToken.generate(user_id=42, email="repeat@example.com")
    token_b = UnsubscribeToken.generate(user_id=42, email="repeat@example.com")

    assert token_a == token_b


def test_str_returns_value(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify str(token) returns the raw hex digest stored in value.

    URL construction and template rendering use str() for interpolation.
    Returning token.value directly from __str__ keeps the string
    representation consistent with attribute access and avoids double-wrapping.
    """
    monkeypatch.setenv("SECRET_KEY", "test-secret")

    token = UnsubscribeToken.generate(user_id=1, email="user@example.com")

    assert str(token) == token.value
