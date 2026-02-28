"""ModerateCommentCommand for admin comment moderation.

This module defines the command object for moderating a comment.
Supports approve, reject, and flag actions. Admin-only operation.
Part of the Discussion bounded context application layer.
"""

from dataclasses import dataclass

_VALID_ACTIONS = frozenset({"approve", "reject", "flag"})


@dataclass(frozen=True)
class ModerateCommentCommand:
    """Command to moderate a comment as an admin.

    Validates primitive constraints at the command boundary. Authorization
    (admin-only) is enforced in the handler based on user_role.

    Attributes:
        comment_id: Positive integer referencing the target Comment.
        action: Moderation action — one of "approve", "reject", "flag".
        moderator_id: Positive integer of the admin performing the action.
        user_role: Role string verified as "admin" in the handler.
    """

    comment_id: int
    action: str
    moderator_id: int
    user_role: str

    def __post_init__(self) -> None:
        """Validate primitive constraints before the command is dispatched.

        Raises:
            ValueError: If comment_id is not greater than zero.
            ValueError: If action is not one of approve/reject/flag.
            ValueError: If moderator_id is not greater than zero.
            ValueError: If user_role is empty.
        """
        if self.comment_id <= 0:
            raise ValueError("comment_id must be greater than 0")

        if self.action not in _VALID_ACTIONS:
            raise ValueError(
                f"action must be one of {sorted(_VALID_ACTIONS)!r},"
                f" got {self.action!r}"
            )

        if self.moderator_id <= 0:
            raise ValueError("moderator_id must be greater than 0")

        if not self.user_role:
            raise ValueError("user_role must not be empty")
