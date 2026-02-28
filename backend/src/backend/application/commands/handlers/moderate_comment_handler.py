"""Handler for ModerateCommentCommand."""

import logging

from backend.application.commands.moderate_comment_command import (
    ModerateCommentCommand,
)
from backend.domain.aggregates.comment import Comment
from backend.infrastructure.persistence.comment_repository import (
    CommentRepository,
)

logger = logging.getLogger(__name__)


def handle_moderate_comment(
    command: ModerateCommentCommand,
    comment_repository: CommentRepository,
) -> Comment:
    """Handle ModerateCommentCommand to approve, reject, or flag a comment.

    Admin-only operation. Orchestration steps:
    1. Verify the requesting user holds the admin role.
    2. Load the comment; raise ValueError if not found.
    3. Execute the action:
       - "approve": clear is_pending_moderation, save and return comment.
       - "reject": soft-delete the comment, save and return comment.
       - "flag": set is_pending_moderation, save and return comment.

    Args:
        command: ModerateCommentCommand carrying comment_id, action,
            moderator_id, and user_role.
        comment_repository: CommentRepository used to load and update
            the comment.

    Returns:
        Updated Comment aggregate reflecting the moderation action.

    Raises:
        ValueError: If user_role is not "admin".
        ValueError: If the comment does not exist.
    """
    if command.user_role != "admin":
        logger.warning(
            "Non-admin user %d (role=%s) attempted moderation on comment %d",
            command.moderator_id,
            command.user_role,
            command.comment_id,
        )
        raise ValueError("Moderation requires admin role")

    logger.debug(
        "Loading comment %d for moderation (action=%s)",
        command.comment_id,
        command.action,
    )
    comment = comment_repository.find_by_id(command.comment_id)
    if comment is None:
        raise ValueError(f"Comment {command.comment_id} not found")

    match command.action:
        case "approve":
            logger.info(
                "Admin %d approving comment %d",
                command.moderator_id,
                command.comment_id,
            )
            comment.approve()
            return comment_repository.save(comment)

        case "reject":
            logger.info(
                "Admin %d rejecting comment %d",
                command.moderator_id,
                command.comment_id,
            )
            comment.mark_as_deleted()
            return comment_repository.save(comment)

        case "flag":
            logger.info(
                "Admin %d flagging comment %d for moderation",
                command.moderator_id,
                command.comment_id,
            )
            comment.mark_as_pending_moderation()
            return comment_repository.save(comment)

        case _:
            raise ValueError(f"Unknown moderation action: {command.action!r}")
