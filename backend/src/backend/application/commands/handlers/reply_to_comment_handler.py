"""Handler for ReplyToCommentCommand."""

import logging

from backend.application.commands.handlers._rate_limit_helper import (
    enforce_rate_limit,
)
from backend.application.commands.reply_to_comment_command import (
    ReplyToCommentCommand,
)
from backend.domain.aggregates.comment import Comment
from backend.infrastructure.moderation.rate_limit_service import (
    RateLimitService,
)
from backend.infrastructure.moderation.spam_check_service import (
    SpamCheckService,
)
from backend.infrastructure.persistence.comment_repository import (
    CommentRepository,
)

logger = logging.getLogger(__name__)


def handle_reply_to_comment(
    command: ReplyToCommentCommand,
    rate_limit_service: RateLimitService,
    spam_check_service: SpamCheckService,
    comment_repository: CommentRepository,
) -> Comment:
    """Handle ReplyToCommentCommand to create a reply to an existing comment.

    Orchestrates reply submission in five steps:
    1. Verify parent comment exists and belongs to the given post.
    2. Rate limit check — raises RateLimitExceededError when exhausted.
    3. Spam check — flags comment for moderation when score >= 50.
    4. Comment creation via domain factory with parent_id set.
    5. Persistence — saves and returns the persisted aggregate.

    Args:
        command: ReplyToCommentCommand carrying post_id, parent_comment_id,
            author_id, text, ip_address, and is_admin.
        rate_limit_service: RateLimitService used to check and record
            submission timestamps.
        spam_check_service: SpamCheckService used to score the reply text.
        comment_repository: CommentRepository used to verify parent
            existence and persist the reply.

    Returns:
        Persisted Comment aggregate with parent_id set, optionally
        flagged for moderation.

    Raises:
        ValueError: If parent comment does not exist or belongs to a
            different post.
        RateLimitExceededError: If the per-user submission window is full.
    """
    logger.debug(
        "Loading parent comment %d for post %d",
        command.parent_comment_id,
        command.post_id,
    )
    parent = comment_repository.find_by_id(command.parent_comment_id)
    if parent is None:
        raise ValueError(
            f"Parent comment {command.parent_comment_id} not found"
        )
    if parent.post_id != command.post_id:
        raise ValueError(
            f"Parent comment {command.parent_comment_id} does not belong"
            f" to post {command.post_id}"
        )
    identifier = f"user:{command.author_id}"
    enforce_rate_limit(
        identifier=identifier,
        ip=command.ip_address,
        is_admin=command.is_admin,
        rate_limit_service=rate_limit_service,
    )

    spam_score = spam_check_service.check(command.text)
    is_spam = spam_score >= 50

    logger.info(
        "Creating reply by author %d on post %d (parent %d)",
        command.author_id,
        command.post_id,
        command.parent_comment_id,
    )
    comment = Comment.create(
        post_id=command.post_id,
        author_id=command.author_id,
        text=command.text,
        parent_id=command.parent_comment_id,
    )

    if is_spam:
        comment.mark_as_pending_moderation()

    return comment_repository.save(comment)
