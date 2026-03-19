"""UnsubscribeToken value object for email unsubscribe link verification."""

import hashlib
import hmac
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class UnsubscribeToken:
    """HMAC-SHA256 token for verifying email unsubscribe requests.

    Generates and verifies per-user tokens for unsubscribe URLs without
    storing tokens in the database. The server recomputes the token from
    user_id, email, and a monthly time bucket to verify it, using a
    constant-time comparison to prevent timing attacks.

    Tokens naturally expire after approximately one month because the time
    bucket changes each calendar month. Verification accepts both the
    current and previous month buckets to accommodate tokens generated near
    a month boundary.

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
    def _current_time_bucket(cls) -> str:
        """Return the current UTC month as YYYYMM string.

        Returns:
            Current UTC year and month formatted as a six-digit string.
        """
        now = datetime.now(UTC)
        return now.strftime("%Y%m")

    @classmethod
    def _prev_time_bucket(cls) -> str:
        """Return the previous UTC month as YYYYMM string.

        Returns:
            Previous UTC year and month formatted as a six-digit string.
        """
        now = datetime.now(UTC)
        if now.month == 1:
            return f"{now.year - 1}12"
        return f"{now.year}{now.month - 1:02d}"

    @classmethod
    def generate(
        cls, user_id: int, email: str, time_bucket: str | None = None
    ) -> "UnsubscribeToken":
        """Generate a time-bucketed HMAC-SHA256 token.

        The token embeds the current UTC month so that tokens naturally expire
        after approximately one month. Using a time bucket instead of a random
        nonce avoids database storage while still bounding the token lifetime.

        Args:
            user_id: Positive integer identifying the user.
            email: Email address the token is scoped to.
            time_bucket: Optional YYYYMM string override for testing. Defaults
                to the current UTC month.

        Returns:
            UnsubscribeToken whose value is the lowercase hex digest.
        """
        bucket = (
            time_bucket
            if time_bucket is not None
            else cls._current_time_bucket()
        )
        secret = os.environ["SECRET_KEY"].encode()
        message = f"{user_id}:{email.lower()}:{bucket}".encode()
        digest = hmac.new(secret, message, hashlib.sha256).hexdigest()
        return cls(digest)

    @classmethod
    def verify(cls, token: str, user_id: int, email: str) -> bool:
        """Verify a token against current and previous month buckets.

        Checks both the current UTC month and the previous month to accommodate
        tokens generated near a month boundary. Returns True if either matches.

        Args:
            token: Hex string from the unsubscribe link to verify.
            user_id: User ID the token must match.
            email: Email address the token must match.

        Returns:
            True if token matches either the current or previous month bucket.
        """
        for bucket in (cls._current_time_bucket(), cls._prev_time_bucket()):
            try:
                expected = cls.generate(
                    user_id=user_id, email=email, time_bucket=bucket
                )
            except (ValueError, TypeError, KeyError):
                continue
            if hmac.compare_digest(token.lower(), expected.value):
                return True
        return False

    def __str__(self) -> str:
        """Return the hex digest string.

        Returns:
            The lowercase hex HMAC-SHA256 digest.
        """
        return self.value
