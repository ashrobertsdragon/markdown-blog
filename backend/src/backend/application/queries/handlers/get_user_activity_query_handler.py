"""Handler for GetUserActivityQuery."""

import logging
from typing import TYPE_CHECKING

from backend.application.queries.get_user_activity_query import (
    GetUserActivityQuery,
    UserActivity,
)

if TYPE_CHECKING:
    from backend.infrastructure.persistence.comment_repository import (
        CommentRepository,
    )
    from backend.infrastructure.persistence.post_repository import (
        PostRepository,
    )
    from backend.infrastructure.persistence.user_repository import (
        UserRepository,
    )

logger = logging.getLogger(__name__)


def get_user_activity_query_handler(
    query: GetUserActivityQuery,
    user_repo: "UserRepository",
    post_repo: "PostRepository",
    comment_repo: "CommentRepository",
) -> UserActivity:
    """Return an activity summary for the requested user.

    Aggregates data from three repositories to produce a UserActivity
    result containing total post and comment counts together with the
    most recent posts and comments.

    Args:
        query: GetUserActivityQuery carrying the target user_id.
        user_repo: UserRepository used to verify the user exists.
        post_repo: PostRepository used to count and list posts.
        comment_repo: CommentRepository used to count and list comments.

    Returns:
        UserActivity with last_login, posts_count, comments_count,
        recent_posts (up to 5), and recent_comments (up to 10).

    Raises:
        ValueError: If no user with query.user_id exists.
    """
    logger.debug("Loading user %d for activity query", query.user_id)
    user = user_repo.find_by_id(query.user_id)
    if user is None:
        raise ValueError(f"User {query.user_id} not found")

    logger.debug("Fetching post activity for user %d", query.user_id)
    recent_posts = post_repo.find_by_author(query.user_id, limit=5)
    posts_count = post_repo.count_by_author(query.user_id)

    logger.debug("Fetching comment activity for user %d", query.user_id)
    recent_comments = comment_repo.find_by_author(query.user_id, limit=10)
    comments_count = comment_repo.count_by_author(query.user_id)

    logger.info(
        "User %d activity: %d posts, %d comments",
        query.user_id,
        posts_count,
        comments_count,
    )

    return UserActivity(
        last_login=None,
        posts_count=posts_count,
        comments_count=comments_count,
        recent_posts=recent_posts,
        recent_comments=recent_comments,
    )
