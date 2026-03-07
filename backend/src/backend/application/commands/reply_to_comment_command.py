"""ReplyToCommentCommand for comment reply submission.

This module defines the command object for posting a reply to an existing
comment on a blog post. Part of the Discussion bounded context application
layer.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ReplyToCommentCommand:
    """Command to post a reply to an existing comment on a blog post.

    Validates primitive constraints at the command boundary. Domain
    validation (CommentText invariants, positive IDs) is enforced by the
    Comment aggregate. Authorization and rate limiting are enforced in the
    handler.

    Attributes:
        post_id: Positive integer referencing the target Post.
        parent_comment_id: Positive integer referencing the parent Comment.
        author_id: Positive integer referencing the replying User.
        text: Raw reply body; must be 1–5000 chars after stripping.
        ip_address: Remote IP address used for rate limit fallback keying.
        is_admin: When True, bypasses rate limit checks in the handler.
            MUST be derived exclusively from the authenticated session role.
            Never source this value from request body or query parameters.
    """

    post_id: int
    parent_comment_id: int
    author_id: int
    text: str
    ip_address: str
    is_admin: bool = False

    def __post_init__(self) -> None:
        """Validate primitive constraints before the command is dispatched.

        Raises:
            ValueError: If post_id is not greater than zero.
            ValueError: If parent_comment_id is not greater than zero.
            ValueError: If author_id is not greater than zero.
            ValueError: If text (stripped) is empty or exceeds 5000 chars.
            ValueError: If ip_address is empty.
        """
        if self.post_id <= 0:
            raise ValueError("post_id must be greater than 0")

        if self.parent_comment_id <= 0:
            raise ValueError("parent_comment_id must be greater than 0")

        if self.author_id <= 0:
            raise ValueError("author_id must be greater than 0")

        stripped = self.text.strip()
        if not stripped:
            raise ValueError("text must not be empty or whitespace-only")
        if len(stripped) > 5000:
            raise ValueError(
                f"text length {len(stripped)} exceeds maximum "
                "of 5000 characters"
            )

        if not self.ip_address:
            raise ValueError("ip_address must not be empty")
