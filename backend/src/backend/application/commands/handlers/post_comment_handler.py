"""Handler for PostCommentCommand.

This module implements the handler function that orchestrates comment
submission through rate limiting, spam detection, and aggregate creation.
"""

import time

from backend.application.commands.post_comment_command import PostCommentCommand
from backend.domain.aggregates.comment import Comment
from backend.exceptions import RateLimitExceededError
from backend.infrastructure.moderation.rate_limit_service import (
    RateLimitService,
)
from backend.infrastructure.moderation.spam_check_service import (
    SpamCheckService,
)


def handle_post_comment(
    command: PostCommentCommand,
    rate_limit_service: RateLimitService,
    spam_check_service: SpamCheckService,
) -> Comment:
    """Handle PostCommentCommand to create a new comment on a blog post.

    Orchestrates comment submission in three steps:
    1. Rate limit check — rejects the request with RateLimitExceededError
       when the per-user window is exhausted.
    2. Spam check — flags the comment for moderation when the score
       meets or exceeds the threshold of 50.
    3. Comment creation — builds the Comment aggregate via the domain
       factory; persistence is deferred to the caller (Task 3).

    Args:
        command: PostCommentCommand carrying post_id, author_id, text,
            ip_address, and is_admin.
        rate_limit_service: RateLimitService used to check and record
            submission timestamps.
        spam_check_service: SpamCheckService used to score the comment
            text for spam signals.

    Returns:
        Comment aggregate, optionally flagged for moderation, with id=None
        (not yet persisted).

    Raises:
        RateLimitExceededError: If the per-user submission window is full.
        ValueError: If domain validation fails inside Comment.create().
    """
    identifier = f"user:{command.author_id}"

    allowed = rate_limit_service.check_limit(
        identifier=identifier,
        ip=command.ip_address,
        is_admin=command.is_admin,
    )

    if not allowed:
        reset_timestamp = rate_limit_service.get_reset_time(identifier)
        reset_after = int(reset_timestamp - time.time())
        raise RateLimitExceededError(
            f"Too many comments. Please wait {reset_after} seconds.",
            reset_after=reset_after,
            remaining=0,
        )

    spam_score = spam_check_service.check(command.text)
    is_spam = spam_score >= 50

    comment = Comment.create(
        post_id=command.post_id,
        author_id=command.author_id,
        text=command.text,
    )

    if is_spam:
        comment.mark_as_pending_moderation()

    return comment
