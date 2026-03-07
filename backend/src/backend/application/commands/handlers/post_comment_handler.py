"""Handler for PostCommentCommand.

This module implements the handler function that orchestrates comment
submission through rate limiting, spam detection, and aggregate creation.
"""

from backend.application.commands.handlers._rate_limit_helper import (
    enforce_rate_limit,
)
from backend.application.commands.post_comment_command import PostCommentCommand
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


def handle_post_comment(
    command: PostCommentCommand,
    rate_limit_service: RateLimitService,
    spam_check_service: SpamCheckService,
    comment_repository: CommentRepository,
) -> Comment:
    """Handle PostCommentCommand to create and persist a new comment.

    Orchestrates comment submission in four steps:
    1. Rate limit check — rejects the request with RateLimitExceededError
       when the per-user window is exhausted.
    2. Spam check — flags the comment for moderation when the score
       meets or exceeds the threshold of 50.
    3. Comment creation — builds the Comment aggregate via the domain
       factory.
    4. Persistence — saves the comment and returns the persisted aggregate.

    Args:
        command: PostCommentCommand carrying post_id, author_id, text,
            ip_address, and is_admin.
        rate_limit_service: RateLimitService used to check and record
            submission timestamps.
        spam_check_service: SpamCheckService used to score the comment
            text for spam signals.
        comment_repository: CommentRepository used to persist the comment.

    Returns:
        Persisted Comment aggregate, optionally flagged for moderation.

    Raises:
        RateLimitExceededError: If the per-user submission window is full.
        ValueError: If domain validation fails inside Comment.create().
    """
    identifier = f"user:{command.author_id}"
    enforce_rate_limit(
        identifier=identifier,
        ip=command.ip_address,
        is_admin=command.is_admin,
        rate_limit_service=rate_limit_service,
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

    return comment_repository.save(comment)
