"""Handler for DeleteCommentCommand."""

import logging

from backend.application.commands.delete_comment_command import (
    DeleteCommentCommand,
)
from backend.exceptions import AuthorizationError
from backend.infrastructure.persistence.comment_repository import (
    CommentRepository,
)

logger = logging.getLogger(__name__)


def handle_delete_comment(
    command: DeleteCommentCommand,
    comment_repository: CommentRepository,
) -> bool:
    """Handle DeleteCommentCommand to remove a comment.

    Supports two deletion modes determined by the requester's role:
    - Admin: soft delete (sets is_deleted=True, preserves text for audit).
    - Author: hard delete (permanent row removal).

    Orchestration steps:
    1. Load comment from repository; raise ValueError if not found.
    2. Authorize: admin → soft delete; own comment → hard delete;
       otherwise raise ValueError.
    3. Call the appropriate repository deletion method.
    4. Return True on success.

    Args:
        command: DeleteCommentCommand carrying comment_id, author_id,
            and user_role.
        comment_repository: CommentRepository used to load and delete
            the comment.

    Returns:
        True when the comment was successfully deleted.

    Raises:
        ValueError: If the comment does not exist.
        AuthorizationError: If the requesting user is neither admin nor
            the comment author.
    """
    logger.debug("Loading comment %d for deletion", command.comment_id)
    comment = comment_repository.find_by_id(command.comment_id)
    if comment is None:
        raise ValueError(f"Comment {command.comment_id} not found")

    if command.user_role == "admin":
        logger.info(
            "Admin %d soft-deleting comment %d",
            command.author_id,
            command.comment_id,
        )
        comment.mark_as_deleted()
        comment_repository.save(comment)
        return True

    if comment.author_id == command.author_id:
        logger.info(
            "Author %d hard-deleting comment %d",
            command.author_id,
            command.comment_id,
        )
        deleted = comment_repository.hard_delete(command.comment_id)
        if not deleted:
            raise ValueError(
                f"Comment {command.comment_id} could not be deleted"
            )
        return True

    logger.warning(
        "User %d (role=%s) attempted to delete comment %d owned by %d",
        command.author_id,
        command.user_role,
        command.comment_id,
        comment.author_id,
    )
    raise AuthorizationError("Cannot delete another user's comment")
