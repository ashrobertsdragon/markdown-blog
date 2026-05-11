"""DeleteCommentCommand for comment removal.

This module defines the command object for deleting a comment. Supports
both author self-deletion (hard delete) and admin moderation (soft delete).
Part of the Discussion bounded context application layer.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DeleteCommentCommand:
    """Command to delete a comment from a blog post.

    Validates primitive constraints at the command boundary. Authorization
    logic (owner vs admin) is enforced in the handler based on user_role.

    Attributes:
        comment_id: Positive integer referencing the target Comment.
        author_id: Positive integer of the user attempting the deletion.
        user_role: Role string for authorization checks in the handler.
    """

    comment_id: int
    author_id: int
    user_role: str

    def __post_init__(self) -> None:
        """Validate primitive constraints before the command is dispatched.

        Raises:
            ValueError: If comment_id is not a positive integer.
            ValueError: If author_id is not a positive integer.
            ValueError: If user_role is empty.
        """
        if not isinstance(self.comment_id, int) or self.comment_id <= 0:
            raise ValueError("comment_id must be greater than 0")

        if not isinstance(self.author_id, int) or self.author_id <= 0:
            raise ValueError("author_id must be greater than 0")

        if not self.user_role:
            raise ValueError("user_role must not be empty")
