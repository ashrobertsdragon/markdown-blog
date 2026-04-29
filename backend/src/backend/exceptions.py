"""Custom exception classes for blog API error handling.

This module provides centralized exception definitions used across all
layers of the application (infrastructure, application, API). These
exceptions enable consistent error handling and HTTP response generation
throughout the application.

Exception Hierarchy:
    Exception
    ├── AuthenticationError (401 Unauthorized)
    └── AuthorizationError (403 Forbidden)

Usage Examples:
    Authentication failure:
        >>> raise AuthenticationError("Invalid JWT token")

    Authorization failure:
        >>> raise AuthorizationError(
        ...     "Admin access required",
        ...     required_role="admin"
        ... )

    Catching exceptions:
        >>> try:
        ...     verify_token(token)
        ... except AuthenticationError as e:
        ...     return {"error": e.message}, 401

Error Handlers:
    Flask error handlers for these exceptions are registered in main.py
    via the register_error_handlers() function from
    api.middleware.error_handler.

Notes:
    - These exceptions should be raised from infrastructure adapters,
      application handlers, or API routes
    - Error handlers convert them to JSON responses with appropriate
      HTTP status codes
    - All exception messages should be user-safe (no internal details)
"""


class NotFoundError(ValueError):
    """Raised when a requested resource does not exist. Maps to HTTP 404.

    This exception is a subclass of ValueError for backward compatibility
    with code that catches ValueError. Prefer catching NotFoundError
    explicitly for precise error handling.

    Attributes:
        message: User-facing error description

    Example:
        >>> raise NotFoundError("Post with id 42 not found")
    """

    def __init__(self, message: str) -> None:
        """Initialize not-found error.

        Args:
            message: User-facing error description
        """
        self.message = message
        super().__init__(message)


class AuthenticationError(Exception):
    """Raised when JWT validation fails or user credentials are invalid.

    This exception represents authentication failures (401 Unauthorized),
    such as:
    - Invalid JWT token
    - Expired JWT token
    - Missing authentication credentials
    - Invalid API key

    Attributes:
        message: User-facing error description

    Example:
        >>> raise AuthenticationError("JWT token has expired")
    """

    def __init__(self, message: str) -> None:
        """Initialize authentication error.

        Args:
            message: User-facing error description
        """
        self.message = message
        super().__init__(message)


class AuthorizationError(Exception):
    """Raised when user lacks required permissions for an operation.

    This exception represents authorization failures (403 Forbidden),
    such as:
    - Insufficient role/permissions
    - Attempting to access another user's resource
    - Missing required scope

    Attributes:
        message: User-facing error description
        required_role: Optional role name that was required for the operation

    Example:
        >>> raise AuthorizationError(
        ...     "Admin role required to delete posts",
        ...     required_role="admin"
        ... )
    """

    def __init__(self, message: str, required_role: str | None = None) -> None:
        """Initialize authorization error.

        Args:
            message: User-facing error description
            required_role: Optional role name that was required
        """
        self.message = message
        self.required_role = required_role
        super().__init__(message)


class RateLimitExceededError(Exception):
    """Raised when a user exceeds the comment rate limit. Maps to HTTP 429.

    Attributes:
        message: User-facing description with wait time.
        reset_after: Seconds until the rate limit window resets.
        remaining: Number of allowed submissions left (always 0 when raised).

    Example:
        >>> raise RateLimitExceededError(
        ...     "Too many comments. Please wait 45 seconds.",
        ...     reset_after=45,
        ...     remaining=0,
        ... )
    """

    def __init__(
        self, message: str, reset_after: int | None = None, remaining: int = 0
    ) -> None:
        """Initialize rate limit error.

        Args:
            message: User-facing error description.
            reset_after: Seconds until window resets; defaults to 60.
            remaining: Remaining submissions in current window.
        """
        self.message = message
        self.reset_after = reset_after if reset_after is not None else 60
        self.remaining = remaining
        super().__init__(message)
