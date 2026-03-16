"""UnsubscribeToken value object for email unsubscribe link verification."""

import hashlib
import hmac
import os
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class UnsubscribeToken:
    """HMAC-SHA256 token for verifying email unsubscribe requests.

    Generates and verifies per-user tokens for unsubscribe URLs without
    storing tokens in the database. The server recomputes the token from
    user_id and email to verify it, using a constant-time comparison to
    prevent timing attacks.

    Attributes:
        value: Lowercase hex HMAC-SHA256 digest.

    Raises:
        TypeError: If raw_token is None.
        ValueError: If raw_token is empty, not 64 hex characters, or contains
            non-hex characters.
    """

    _DIGEST_LENGTH = 64

    value: str

    def __init__(self, raw_token: str) -> None:
        """Validate and normalise a raw hex token string.

        Args:
            raw_token: 64-character hex string (HMAC-SHA256 digest).

        Raises:
            TypeError: If raw_token is None.
            ValueError: If raw_token is empty, not 64 chars, or not hex.
        """
        if raw_token is None:
            raise TypeError("UnsubscribeToken cannot be None")
        if not raw_token:
            raise ValueError("UnsubscribeToken cannot be empty")
        normalised = raw_token.lower()
        if len(normalised) != UnsubscribeToken._DIGEST_LENGTH:
            raise ValueError(
                f"UnsubscribeToken must be {UnsubscribeToken._DIGEST_LENGTH}"
                " characters"
            )
        if not re.match(r"^[a-f0-9]+$", normalised):
            raise ValueError(
                "UnsubscribeToken must contain only hexadecimal characters"
            )
        object.__setattr__(self, "value", normalised)

    @classmethod
    def generate(cls, user_id: int, email: str) -> "UnsubscribeToken":
        """Generate a deterministic HMAC-SHA256 token for a user/email pair.

        Uses the SECRET_KEY environment variable as the HMAC key and
        encodes the message as ``{user_id}:{email}``. The same inputs
        always produce the same token, enabling stateless verification.

        Args:
            user_id: Positive integer identifying the user.
            email: Email address the token is scoped to.

        Returns:
            UnsubscribeToken whose value is the lowercase hex digest.
        """
        secret = os.environ["SECRET_KEY"].encode()
        message = f"{user_id}:{email.lower()}".encode()
        digest = hmac.new(secret, message, hashlib.sha256).hexdigest()
        return cls(digest)

    @classmethod
    def verify(cls, token: str, user_id: int, email: str) -> bool:
        """Verify a token string against the expected value for user/email.

        Recomputes the expected token and uses hmac.compare_digest for a
        constant-time comparison that prevents timing-based token guessing.

        Args:
            token: Hex string from the unsubscribe link to verify.
            user_id: User ID the token must match.
            email: Email address the token must match.

        Returns:
            True if token matches the expected digest, False otherwise.
        """
        try:
            expected = cls.generate(user_id=user_id, email=email)
        except (ValueError, TypeError):
            return False
        return hmac.compare_digest(token.lower(), expected.value)

    def __str__(self) -> str:
        """Return the hex digest string.

        Returns:
            The lowercase hex HMAC-SHA256 digest.
        """
        return self.value
